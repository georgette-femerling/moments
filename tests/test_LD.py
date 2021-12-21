import os
import unittest

import numpy as np
import scipy.special
import moments
import moments.LD
import moments.TwoLocus
import pickle
import time
import copy


class LDTestCase(unittest.TestCase):
    def setUp(self):
        self.startTime = time.time()

    def tearDown(self):
        t = time.time() - self.startTime
        print("%s: %.3f seconds" % (self.id(), t))

    def test_steady_state_fs(self):
        theta = 0.001
        fs = moments.Demographics1D.snm([20]) * theta
        y = moments.LD.Demographics1D.snm(theta=theta)
        self.assertTrue(np.allclose(y[-1][0], fs.project([2])))
        y = y.split(0)
        fs = moments.Manips.split_1D_to_2D(fs, 10, 10)
        fs_proj = fs.project([1, 1])
        self.assertTrue(np.allclose(y[-1][1], fs_proj[0, 1] + fs_proj[1, 0]))

    def test_migration_symmetric_2D(self):
        theta = 0.001
        fs = moments.Demographics1D.snm([30]) * theta
        y = moments.LD.Demographics1D.snm(theta=theta)
        m = 1.0
        T = 0.3
        y = y.split(0)
        y.integrate([1, 1], T, m=[[0, m], [m, 0]], theta=theta)
        fs = moments.Manips.split_1D_to_2D(fs, 15, 15)
        fs.integrate([1, 1], T, m=[[0, m], [m, 0]], theta=theta)
        fs_proj = fs.project([1, 1])
        self.assertTrue(np.allclose(y[-1][1], fs_proj[0, 1] + fs_proj[1, 0], rtol=1e-3))

    def test_migration_asymmetric_2D(self):
        theta = 0.001
        fs = moments.Demographics1D.snm([60]) * theta
        y = moments.LD.Demographics1D.snm(theta=theta)
        m12 = 10.0
        m21 = 0.0
        T = 2.0
        y = y.split(0)
        y.integrate([1, 1], T, m=[[0, m12], [m21, 0]], theta=theta)
        fs = moments.Manips.split_1D_to_2D(fs, 30, 30)
        fs.integrate([1, 1], T, m=[[0, m12], [m21, 0]], theta=theta)
        fs_proj = fs.project([1, 1])
        self.assertTrue(np.allclose(y[-1][1], fs_proj[0, 1] + fs_proj[1, 0], rtol=1e-3))
        fs_proj = fs.marginalize([1]).project([2])
        self.assertTrue(np.allclose(y[-1][0], fs_proj[1], rtol=1e-3))
        fs_proj = fs.marginalize([0]).project([2])
        self.assertTrue(np.allclose(y[-1][2], fs_proj[1], rtol=1e-3))

    def test_equilibrium_ld_tlfs_cache(self):
        theta = 1
        rhos = [0, 1, 10]
        y = moments.LD.Demographics1D.snm(theta=theta, rho=rhos)
        ns = 30
        for ii, rho in enumerate(rhos):
            F = moments.TwoLocus.Demographics.equilibrium(ns, rho=rho).project(4)
            self.assertTrue(np.allclose(y[ii], [F.D2(), F.Dz(), F.pi2()], rtol=5e-2))


class SplitStats(unittest.TestCase):
    def setUp(self):
        self.startTime = time.time()

    def tearDown(self):
        t = time.time() - self.startTime
        print("%s: %.3f seconds" % (self.id(), t))

    def test_split_het(self):
        h = [1]
        h_split_1 = moments.LD.Numerics.split_h(h, 0, 1)
        self.assertEqual(len(h_split_1), 3)
        self.assertTrue(np.all([x == 1 for x in h_split_1]))
        h_split_2 = moments.LD.Numerics.split_h(h_split_1, 1, 2)
        self.assertEqual(len(h_split_2), 6)
        self.assertTrue(np.all([x == 1 for x in h_split_2]))

    def test_split_ld(self):
        y = [1, 2, 3]
        y_split_1 = moments.LD.Numerics.split_ld(y, 0, 1)
        self.assertEqual(len(y_split_1), len(moments.LD.Util.moment_names(2)[0]))
        self.assertTrue(
            np.all(
                [
                    x == 1
                    for i, x in enumerate(y_split_1)
                    if moments.LD.Util.moment_names(2)[0][i].split("_") == "DD"
                ]
            )
        )
        self.assertTrue(
            np.all(
                [
                    x == 2
                    for i, x in enumerate(y_split_1)
                    if moments.LD.Util.moment_names(2)[0][i].split("_") == "Dz"
                ]
            )
        )
        self.assertTrue(
            np.all(
                [
                    x == 3
                    for i, x in enumerate(y_split_1)
                    if moments.LD.Util.moment_names(2)[0][i].split("_") == "pi2"
                ]
            )
        )

    def test_split_pop_ids(self):
        pass


class SwapPops(unittest.TestCase):
    def setUp(self):
        self.startTime = time.time()

    def tearDown(self):
        t = time.time() - self.startTime
        print("%s: %.3f seconds" % (self.id(), t))

    def test_swap_pops(self):
        rho = [0, 1, 2]
        y = moments.LD.Demographics1D.snm(rho=rho, theta=0.01)
        y = y.split(0)
        y = y.split(1)
        y.integrate([1, 2, 3], 0.01, theta=0.01, rho=rho)
        y_swap = y.swap_pops(0, 1)
        y_swap_back = y_swap.swap_pops(0, 1)
        for u, v in zip(y, y_swap_back):
            self.assertTrue(np.allclose(u, v))

        y.pop_ids = ["A", "B", "C"]
        y_swap = y.swap_pops(1, 2)
        self.assertTrue(
            np.all([x == y for x, y in zip(y_swap.pop_ids, ["A", "C", "B"])])
        )


class MarginalizeStats(unittest.TestCase):
    def setUp(self):
        self.startTime = time.time()

    def tearDown(self):
        t = time.time() - self.startTime
        print("%s: %.3f seconds" % (self.id(), t))

    def test_marginalize(self):
        y = moments.LD.Demographics1D.snm()
        with self.assertRaises(ValueError):
            y.marginalize(0)
        with self.assertRaises(ValueError):
            y.marginalize([0])

        y = y.split(0)
        y = y.split(0)
        with self.assertRaises(ValueError):
            y.marginalize([0, 1, 2])
        y_marg = y.marginalize([0, 2])
        self.assertTrue(y_marg.num_pops == 1)

    def test_marginalize_pop_ids(self):
        y = moments.LD.Demographics1D.snm()
        y = y.split(0)
        y = y.split(0)
        y = y.split(0)
        y = y.split(0)
        y.pop_ids = ["a", "b", "c", "d", "e"]
        self.assertTrue(
            np.all(
                [x == y for x, y in zip(y.marginalize([0, 2]).pop_ids, ["b", "d", "e"])]
            )
        )


class SplitLD(unittest.TestCase):
    def setUp(self):
        self.startTime = time.time()

    def tearDown(self):
        t = time.time() - self.startTime
        print("%s: %.3f seconds" % (self.id(), t))

    def test_split_1D(self):
        y = moments.LD.Demographics1D.snm(rho=[0, 10], pop_ids=["A"])
        y2 = y.split(0, new_ids=["B", "C"])
        for i, m in enumerate(y2.names()[0]):
            mm = m.split("_")[0]
            if mm == "DD":
                self.assertTrue(y2[0][i] == y[0][0])
            elif mm == "Dz":
                self.assertTrue(y2[0][i] == y[0][1])
            elif mm == "pi2":
                self.assertTrue(y2[0][i] == y[0][2])

    def test_split_2D(self):
        y = moments.LD.Demographics2D.split_mig(
            (2.0, 3.0, 0.1, 2.0), rho=1, pop_ids=["A", "B"]
        )
        y_s = y.split(1, new_ids=["C", "D"])
        self.assertTrue(y_s.pop_ids[0] == "A")
        self.assertTrue(y_s.pop_ids[1] == "C")
        self.assertTrue(y_s.pop_ids[2] == "D")
        self.assertTrue(
            y_s[0][y_s.names()[0].index("DD_1_2")] == y[0][y.names()[0].index("DD_1_1")]
        )
        self.assertTrue(
            y_s[0][y_s.names()[0].index("pi2_0_1_0_2")]
            == y[0][y.names()[0].index("pi2_0_1_0_1")]
        )

    def test_split_pop_ids(self):
        y = moments.LD.Demographics1D.snm(pop_ids=["a"])
        y = y.split(0, new_ids=["b", "c"])
        self.assertTrue(len(y.pop_ids) == 2)
        self.assertTrue(y.pop_ids[0] == "b")
        self.assertTrue(y.pop_ids[1] == "c")


class MergeLD(unittest.TestCase):
    def setUp(self):
        self.startTime = time.time()

    def tearDown(self):
        t = time.time() - self.startTime
        print("%s: %.3f seconds" % (self.id(), t))

    def test_merge_two_pops(self):
        y = moments.LD.Demographics2D.split_mig(
            (1, 2, 0.1, 2), rho=1, pop_ids=["A", "B"]
        )
        with self.assertRaises(ValueError):
            y.merge(0, 1, 1.5)
        with self.assertRaises(ValueError):
            y.merge(0, 0, 0.5)
        with self.assertRaises(ValueError):
            y.merge(0, 2, 0.5)

        y1 = y.merge(0, 1, 0.5)
        self.assertTrue(y1.num_pops == 1)
        self.assertTrue(y1.pop_ids[0] == "Merged")

        y2 = y.merge(0, 1, 0.1, new_id="XX")
        self.assertTrue(y2.pop_ids[0] == "XX")


class AdmixLD(unittest.TestCase):
    def setUp(self):
        self.startTime = time.time()

    def tearDown(self):
        t = time.time() - self.startTime
        print("%s: %.3f seconds" % (self.id(), t))

    def test_admix_two_pops(self):
        y = moments.LD.Demographics2D.split_mig(
            (1, 2, 0.1, 2), rho=1, pop_ids=["A", "B"]
        )
        with self.assertRaises(ValueError):
            y.admix(0, 1, 1.5)
        with self.assertRaises(ValueError):
            y.admix(0, 0, 0.5)
        with self.assertRaises(ValueError):
            y.admix(0, 2, 0.5)

        y1 = y.admix(0, 1, 0.5)
        self.assertTrue(y1.num_pops == 3)
        self.assertTrue(y1.pop_ids[0] == "A")
        self.assertTrue(y1.pop_ids[1] == "B")
        self.assertTrue(y1.pop_ids[2] == "Adm")

        y2 = y.admix(0, 1, 0.1, new_id="XX")
        self.assertTrue(y2.pop_ids[2] == "XX")

        y3 = y.merge(0, 1, 0.1, new_id="XX")
        y2 = y2.marginalize([0, 1])
        self.assertTrue(np.all(y3[0] == y2[0]))
        self.assertTrue(y3.pop_ids[0] == y2.pop_ids[0])


class PulseLD(unittest.TestCase):
    def setUp(self):
        self.startTime = time.time()

    def tearDown(self):
        t = time.time() - self.startTime
        print("%s: %.3f seconds" % (self.id(), t))

    def test_pulse_two_pops(self):
        y = moments.LD.Demographics2D.split_mig(
            (1, 2, 0.1, 2), rho=1, pop_ids=["A", "B"]
        )
        with self.assertRaises(ValueError):
            y.pulse_migrate(0, 1, 1.5)
        with self.assertRaises(ValueError):
            y.pulse_migrate(0, 0, 0.5)
        with self.assertRaises(ValueError):
            y.pulse_migrate(0, 2, 0.5)

        y1 = y.pulse_migrate(0, 1, 0.1)
        self.assertTrue(y1.num_pops == 2)
        self.assertTrue(y1.pop_ids[0] == "A")
        self.assertTrue(y1.pop_ids[1] == "B")
        y2 = y.merge(0, 1, 0.1)
        y1 = y1.marginalize([0])
        self.assertTrue(np.all(y1[0] == y2[0]))


class TestDemographics1D(unittest.TestCase):
    def setUp(self):
        self.startTime = time.time()

    def tearDown(self):
        t = time.time() - self.startTime
        print("%s: %.3f seconds" % (self.id(), t))

    def check_order(self, y_high, y_low):
        for m, x in zip(y_high.names()[0], y_high[0]):
            if m in y_low.names()[0]:
                self.assertTrue(x == y_low[0][y_low.names()[0].index(m)])

    def test_snm(self):
        y = moments.LD.Demographics1D.snm()
        self.assertEqual(len(y), 1)
        self.assertTrue(np.isclose(y[0][0], 0.001))

        y = moments.LD.Demographics1D.snm(pop_ids=["A"])
        self.assertTrue(y.pop_ids[0] == "A")

        y = moments.LD.Demographics1D.snm(rho=1.0)
        self.assertEqual(len(y), 2)

        y_0 = moments.LD.Demographics1D.snm(rho=0)
        y_1 = moments.LD.Demographics1D.snm(rho=1)
        y_0_1 = moments.LD.Demographics1D.snm(rho=[0, 1])
        self.assertTrue(np.allclose(y_0[0], y_0_1[0]))
        self.assertTrue(np.allclose(y_1[0], y_0_1[1]))

    def test_snm_order(self):
        rho = 1.5
        y2 = moments.LD.Demographics1D.snm(order=2, rho=rho)
        y4 = moments.LD.Demographics1D.snm(order=4, rho=rho)
        y6 = moments.LD.Demographics1D.snm(order=6, rho=rho)
        self.check_order(y6, y4)
        self.check_order(y4, y2)

    def test_two_epoch(self):
        y_snm = moments.LD.Demographics1D.snm(rho=1)
        y_2epoch = moments.LD.Demographics1D.two_epoch((1, 0.1), rho=1)
        self.assertTrue(np.allclose(y_snm[0], y_2epoch[0]))

        y_8 = moments.LD.Demographics1D.two_epoch(
            (2.0, 0.3), rho=2, theta=0.01, order=8, pop_ids=["XX"]
        )
        y_4 = moments.LD.Demographics1D.two_epoch(
            (2.0, 0.3), rho=2, theta=0.01, order=3, pop_ids=["XX"]
        )
        self.check_order(y_8, y_4)
        self.assertTrue(y_8.pop_ids[0] == y_4.pop_ids[0])

    def test_three_epoch(self):
        y_snm = moments.LD.Demographics1D.snm(rho=5, theta=0.05, pop_ids=["a"])
        y_3 = moments.LD.Demographics1D.three_epoch(
            (1, 1, 0.1, 0.1), rho=5, theta=0.05, pop_ids=["a"]
        )
        self.assertTrue(y_snm.pop_ids[0] == y_3.pop_ids[0])
        self.assertTrue(np.allclose(y_snm[0], y_3[0]))
        self.assertTrue(np.allclose(y_snm[1], y_3[1]))

        y_2 = moments.LD.Demographics1D.two_epoch((2, 0.1), rho=1)
        y_3a = moments.LD.Demographics1D.three_epoch((2, 2, 0.075, 0.025), rho=1)
        y_3b = moments.LD.Demographics1D.three_epoch((1, 2, 0.1, 0.1), rho=1)
        self.assertTrue(np.allclose(y_2[0], y_3a[0]))
        self.assertTrue(np.allclose(y_2[1], y_3a[1]))
        self.assertTrue(np.allclose(y_2[0], y_3b[0]))
        self.assertTrue(np.allclose(y_2[1], y_3b[1]))


class CopyAndPickle(unittest.TestCase):
    def setUp(self):
        self.startTime = time.time()

    def tearDown(self):
        t = time.time() - self.startTime
        print("%s: %.3f seconds" % (self.id(), t))

    def test_copy(self):
        y = moments.LD.Demographics2D.snm(rho=[0, 1, 2], pop_ids=["A", "B"])
        y2 = copy.deepcopy(y)

    def test_pickle(self):
        y = moments.LD.Demographics2D.snm(rho=[0, 1, 2], pop_ids=["A", "B"])
        temp_file = "temp.bp"
        with open(temp_file, "wb+") as fout:
            pickle.dump(y, fout)
        y2 = pickle.load(open(temp_file, "rb"))
        self.assertEqual(y.num_pops, y2.num_pops)
        self.assertEqual(y.pop_ids, y2.pop_ids)
        for x1, x2 in zip(y[:], y2[:]):
            self.assertTrue(np.all(x1 == x2))
        os.remove(temp_file)
