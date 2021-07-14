import numpy as np
import moments.LD

# parameters for out of africa model
Taf = 0.265
Tb = 0.342 - 0.265
Tf = 0.405 - 0.342
nu_af = 1.98
nu_b = 0.255
nu_eu0 = 0.141
nu_as0 = 0.0752
nu_euf = 4.65
nu_asf = 6.22
m_af_b = 1.1
m_af_eu = 0.183
m_af_as = 0.57
m_eu_as = 0.227

p = (Taf,Tb,Tf,nu_af,nu_b,nu_eu0,nu_as0,nu_euf,nu_asf,m_af_b,m_af_eu,m_af_as,m_eu_as)

N0 = 7310
u = 2.36e-8
theta = 4*N0*u

def OutOfAfrica(params, rho=0.0, theta=0.0001):
    (Taf,Tb,Tf,nu_af,nu_b,nu_eu0,nu_as0,nu_euf,nu_asf,m_af_b,m_af_eu,m_af_as,m_eu_as) = params
    y = moments.LD.Numerics.root_equilibrium(rho,theta)
    y = moments.LD.LDstats(y)
    y.integrate([nu_af], Taf, rho=rho, theta=theta)
    y = y.split(1)
    y.integrate([nu_af,nu_b], Tb, rho=rho, theta=theta, m=[[0, m_af_b],[m_af_b, 0]])
    y = y.split(2)
    nu_func_eu = lambda t: nu_eu0 * (nu_euf/nu_eu0)**(t/Tf)
    nu_func_as = lambda t: nu_as0 * (nu_asf/nu_as0)**(t/Tf)
    nu_func = lambda t: [nu_af, nu_func_eu(t), nu_func_as(t)]
    y.integrate(nu_func, Tf, rho=rho, theta=theta, m=[[0, m_af_eu, m_af_as],[m_af_eu, 0, m_eu_as],[m_af_as, m_eu_as, 0]])
    return y


rho = 0.0

y = OutOfAfrica(p, rho=rho, theta=theta)

print y
print rho
print y[1]/np.sqrt(y[0]*y[3])
print y[2]/np.sqrt(y[0]*y[5])
print y[4]/np.sqrt(y[3]*y[5])
