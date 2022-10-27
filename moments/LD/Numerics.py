import numpy as np

import copy
import itertools
from scipy.sparse import identity
from scipy.sparse.linalg import factorized
from scipy.sparse import csc_matrix
from scipy.sparse.linalg import inv as spinv
import pickle

from . import Matrices
from . import Util

"""
splits, marginalizations, and other manipulations
"""


def split_h(h, pop_to_split, num_pops):
    h_from = h
    h_new = np.empty(int((num_pops + 1) * (num_pops + 2) / 2))
    c = 0
    hn = Util.het_names(num_pops)
    for ii in range(num_pops + 1):
        for jj in range(ii, num_pops + 1):
            if jj == num_pops:
                if ii == jj:
                    h_new[c] = h_from[hn.index("H_{0}_{0}".format(pop_to_split))]
                else:
                    if ii <= pop_to_split:
                        h_new[c] = h_from[
                            hn.index("H_{0}_{1}".format(ii, pop_to_split))
                        ]
                    else:
                        h_new[c] = h_from[
                            hn.index("H_{0}_{1}".format(pop_to_split, ii))
                        ]
            else:
                h_new[c] = h_from[hn.index("H_{0}_{1}".format(ii, jj))]

            c += 1

    return h_new


def split_ld(y, pop_to_split, num_pops):
    mom_list_from = Util.ld_names(num_pops)
    mom_list_to = Util.ld_names(num_pops + 1)

    y_new = np.ones(len(mom_list_to))
    for ii, mom_to in enumerate(mom_list_to):
        if mom_to in mom_list_from:
            y_new[ii] = y[mom_list_from.index(mom_to)]
        else:
            mom_to_split = mom_to.split("_")
            for jj in range(1, len(mom_to_split)):
                if int(mom_to_split[jj]) == num_pops:
                    mom_to_split[jj] = str(pop_to_split)
            mom_from = "_".join(mom_to_split)
            y_new[ii] = y[mom_list_from.index(Util.map_moment(mom_from))]
    return y_new


def admix_h(h, num_pops, pop1, pop2, f):
    Ah = Matrices.admix_h(num_pops, pop1, pop2, f)
    h_new = Ah.dot(h)
    return h_new


def admix_ld(ys, num_pops, pop1, pop2, f):
    y_new = []
    Ald = Matrices.admix_ld(num_pops, pop1, pop2, f)
    for y in ys:
        y_new.append(Ald.dot(y))
    return y_new


def admix(Y, num_pops, pop1, pop2, f):
    h = Y[-1]
    h_new = admix_h(h, num_pops, pop1, pop2, f)
    if len(Y) > 1:
        ys = Y[:-1]
        ys_new = admix_ld(ys, num_pops, pop1, pop2, f)
        return ys_new + [h_new]
    else:
        return [h_new]


### transition matrices


def drift(num_pops, nus, frozen=None, rho=None):
    Dh = Matrices.drift_h(num_pops, nus, frozen=frozen)
    if rho is not None:
        Dld = Matrices.drift_ld(num_pops, nus, frozen=frozen)
    else:
        Dld = None
    return Dh, Dld


def mutation(num_pops, theta, frozen=None, selfing=None, rho=None):
    ### mutation for ld also has dependence on H
    Uh = Matrices.mutation_h(num_pops, theta, frozen=frozen, selfing=selfing)
    if rho is not None:
        Uld = Matrices.mutation_ld(num_pops, theta, frozen=frozen, selfing=selfing)
    else:
        Uld = None
    return Uh, Uld


def recombination(num_pops, rho=0.0, frozen=None, selfing=None):
    if np.isscalar(rho):
        R = Matrices.recombination(num_pops, rho, frozen=frozen, selfing=selfing)
    else:
        R = [
            Matrices.recombination(num_pops, r, frozen=frozen, selfing=selfing)
            for r in rho
        ]
    return R


def migration(num_pops, m, frozen=None, rho=None):
    Mh = Matrices.migration_h(num_pops, m, frozen=frozen)
    if rho is not None:
        Mld = Matrices.migration_ld(num_pops, m, frozen=frozen)
    else:
        Mld = None
    return Mh, Mld


### integration routines


def integrate(
    Y,
    nu,
    T,
    dt=0.001,
    theta=0.001,
    rho=None,
    m=None,
    num_pops=None,
    selfing=None,
    frozen=None,
):
    """"""
    if num_pops == None:
        num_pops = len(nu)

    h = Y[-1]
    if len(Y) == 2:
        y = Y[0]
    else:
        ys = Y[:-1]

    if callable(nu):
        nus = nu(0)
    else:
        nus = [float(nu_pop) for nu_pop in nu]

    Uh, Uld = mutation(num_pops, theta, frozen=frozen, selfing=selfing, rho=rho)

    if rho is not None:
        # if rho is a scalar, return single matrix, if rho is a list,
        # returns list of matrices
        R = recombination(num_pops, rho=rho, frozen=frozen, selfing=selfing)

    if num_pops > 1 and m is not None:
        if np.any(np.array(m) != 0):
            Mh, Mld = migration(num_pops, m, frozen=frozen, rho=rho)

    dt_last = dt
    nus_last = nus
    elapsed_t = 0

    while elapsed_t < T:
        if elapsed_t + dt > T:
            dt = T - elapsed_t

        if callable(nu):
            nus = nu(elapsed_t + dt / 2.0)

        # recompute matrices if dt or sizes have changed
        if dt != dt_last or nus != nus_last or elapsed_t == 0:
            Dh, Dld = drift(num_pops, nus, frozen=frozen, rho=rho)
            if num_pops > 1 and m is not None and np.any(np.array(m) != 0):
                Ab_h = Dh + Mh
                if rho is not None:
                    if np.isscalar(rho):
                        Ab_ld = Dld + Mld + R
                    else:
                        Ab_ld = [Dld + Mld + R[i] for i in range(len(rho))]
            else:
                Ab_h = Dh
                if rho is not None:
                    if np.isscalar(rho):
                        Ab_ld = Dld + R
                    else:
                        Ab_ld = [Dld + R[i] for i in range(len(rho))]

            # heterozygosity solver
            Ab1_h = np.eye(Ab_h.shape[0]) + dt / 2.0 * Ab_h
            Ab2_h = np.linalg.inv(np.eye(Ab_h.shape[0]) - dt / 2.0 * Ab_h)
            # ld solvers
            if rho is not None:
                if np.isscalar(rho):
                    Ab1_ld = identity(Ab_ld.shape[0], format="csc") + dt / 2.0 * Ab_ld
                    Ab2_ld = factorized(
                        identity(Ab_ld.shape[0], format="csc") - dt / 2.0 * Ab_ld
                    )
                else:
                    Ab1_ld = [
                        identity(Ab_ld[i].shape[0], format="csc") + dt / 2.0 * Ab_ld[i]
                        for i in range(len(rho))
                    ]
                    Ab2_ld = [
                        factorized(
                            identity(Ab_ld[i].shape[0], format="csc")
                            - dt / 2.0 * Ab_ld[i]
                        )
                        for i in range(len(rho))
                    ]

        # forward
        # ld
        if rho is not None:
            if np.isscalar(rho):
                y = Ab1_ld.dot(y) + dt * Uld.dot(h)
            else:
                ys = [Ab1_ld[i].dot(ys[i]) + dt * Uld.dot(h) for i in range(len(ys))]
        # h
        h = Ab1_h.dot(h) + dt * Uh

        # backward
        # ld
        if rho is not None:
            if np.isscalar(rho):
                y = Ab2_ld(y)
            else:
                ys = [Ab2_ld[i](ys[i]) for i in range(len(ys))]
        # h
        h = Ab2_h.dot(h)

        elapsed_t += dt
        dt_last = copy.copy(dt)
        nus_last = copy.copy(nus)

    Y[-1] = h
    if np.isscalar(rho):
        Y[0] = y
    else:
        Y[:-1] = ys

    return Y


def steady_state(theta=0.001, rho=None, selfing_rate=None):
    if theta <= 0:
        raise ValueError("theta must be positive")
    if rho is not None:
        if np.isscalar(rho) and rho < 0:
            raise ValueError("rho cannot be negative")
        if not np.isscalar(rho):
            for r in rho:
                if r < 0:
                    raise ValueError("rho values cannot be negative")
    if selfing_rate is None:
        h_ss = np.array([theta])
    elif not np.isscalar(selfing_rate):
        raise ValueError("selfing rate must be a scalar")
    else:
        if selfing_rate < 0 or selfing_rate > 1:
            raise ValueError("selfing rate must be between 0 and 1")
        h_ss = np.array([theta * (1 - selfing_rate / 2)])
    if hasattr(rho, "__len__"):  # list of rhos
        ys_ss = [
            equilibrium_ld(theta=theta, rho=r, selfing_rate=selfing_rate) for r in rho
        ]
        return ys_ss + [h_ss]
    elif np.isscalar(rho):  # one rho value
        y_ss = equilibrium_ld(theta=theta, rho=rho, selfing_rate=selfing_rate)
        return [y_ss, h_ss]
    else:  # only het stats
        return [h_ss]


def equilibrium_ld(theta=0.001, rho=0.0, selfing_rate=None):
    if selfing_rate is None:
        h_ss = np.array([theta])
    else:
        h_ss = np.array([theta * (1 - selfing_rate / 2)])
    U = Matrices.mutation_ld(1, theta, selfing=[selfing_rate])
    R = Matrices.recombination(1, rho, selfing=[selfing_rate])
    D = Matrices.drift_ld(1, [1.0])
    return factorized(D + R)(-U.dot(h_ss))


def steady_state_two_pop(nus, m, rho=None, theta=0.001, selfing_rate=None):
    nu0, nu1 = nus
    m01 = m[0][1]
    m10 = m[1][0]
    if rho is not None:
        if np.isscalar(rho) and rho < 0:
            raise ValueError("recombination rate cannot be negative")
        elif not np.isscalar(rho):
            for r in rho:
                if r < 0:
                    raise ValueError("recombination rate cannot be negative")
    if theta <= 0:
        raise ValueError("mutation rate must be positive")

    if m01 <= 0 or m10 <= 0 or nu0 <= 0 or nu1 <= 0:
        raise ValueError(
            "migration rates and relative population sizes must be positive"
        )

    if selfing_rate is None:
        selfing_rate = [0, 0]
    elif not hasattr(selfing_rate, "__len__") or len(selfing_rate) != 2:
        raise ValueError("selfing rates must be given as list of length 2")
    else:
        for f in selfing_rate:
            if f < 0 or f > 1:
                raise ValueError("selfing rates must be between 0 and 1")

    # get the two-population steady state of heterozygosity statistics
    Mh = Matrices.migration_h(2, [[0, m01], [m10, 0]])
    Dh = Matrices.drift_h(2, [nu0, nu1])
    Uh = Matrices.mutation_h(2, theta, selfing=selfing_rate)
    h_ss = np.linalg.inv(Mh + Dh).dot(-Uh)

    # get the two-population steady state of LD statistics
    if rho is None:
        return [h_ss]

    def two_pop_ld_ss(nu0, nu1, m01, m10, theta, rho, selfing_rate, h_ss):
        U = Matrices.mutation_ld(2, theta, selfing=selfing_rate)
        R = Matrices.recombination(2, rho, selfing=selfing_rate)
        D = Matrices.drift_ld(2, [nu0, nu1])
        M = Matrices.migration_ld(2, [[0, m01], [m10, 0]])
        return factorized(D + R + M)(-U.dot(h_ss))

    if np.isscalar(rho):
        y_ss = two_pop_ld_ss(nu0, nu1, m01, m10, theta, rho, selfing_rate, h_ss)
        return [y_ss, h_ss]

    y_ss = []
    for r in rho:
        y_ss.append(two_pop_ld_ss(nu0, nu1, m01, m10, theta, r, selfing_rate, h_ss))
    return y_ss + [h_ss]
