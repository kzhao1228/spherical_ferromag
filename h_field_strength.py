import numpy as np
import scipy.special as spc
m = 1       #volume magnetisation
a = 1       #radius of the ferromagnet
h = 1     #thickness of the ferromagnet
theta = np.pi/4 #angle of the magnetisation

def H_spherical_ferromag(x,y,z):
    """The magnetic field of a cylinder ferromagnet"""
    #the loop below is a filter that can rule out several boundary conditions such that 
    #the function works without potential breakdowns. N.B. the loop doesn't delete those
    #elements but adds an increment of 0.01 to make the output value meaningful
    if ((np.any(y==0) and np.any(x==0)) or np.any(z==-h) or np.any(z==0)):
            mod1 = [i for i, j in enumerate(x) if j == 0]
            mod2 = [i for i, j in enumerate(y) if j == 0]
            np.put(x, [mod1], [x[mod1]+0.01])
            np.put(y, [mod2], [y[mod2]+0.01])
            mod3 = [i for i, j in enumerate(z) if j == -h]  
            mod4 = [i for i, j in enumerate(z) if j == 0]
            np.put(z, [mod3,mod4], [z[mod3]+0.01,z[mod4]+0.01])        
    else:
        x = x
        y = y
        z = z
    r = np.sqrt(x**2+y**2)
    z_p = z+h
    sqrt1 = np.sqrt((a**2+z**2+r**2)**2-4*(a**2)*(r**2))
    alp = (((a**2-z**2-r**2)+sqrt1)/((z**2+r**2-a**2)+sqrt1))* \
          (((r**2-z**2-a**2)+sqrt1)/((z**2-r**2+a**2)+sqrt1))
    alp1 = np.sqrt(alp)
    bta1 = np.arcsin(np.sqrt(0.5*(1+((z**2+r**2-a**2)/sqrt1))))
    
    sqrt1_p = np.sqrt((a**2+z_p**2+r**2)**2-4*(a**2)*(r**2))
    alp_p = (((a**2-z_p**2-r**2)+sqrt1_p)/((z_p**2+r**2-a**2)+sqrt1_p))* \
            (((r**2-z_p**2-a**2)+sqrt1_p)/((z_p**2-r**2+a**2)+sqrt1_p))
    alp2 = np.sqrt(alp_p)
    bta2 = np.arcsin(np.sqrt(0.5*(1+((z_p**2+r**2-a**2)/sqrt1_p))))
    def heaviside(z):
        """ step function """
        if np.any(z>0) or np.any(z < -h):
            the_result = 0
        else:
            the_result = 1
        return the_result
    jacobi = np.sign(z)*spc.ellipe(alp1)*spc.ellipkinc(bta1, np.sqrt(1-alp)) \
             -np.sign(z+h)*spc.ellipe(alp2)*spc.ellipkinc(bta2, np.sqrt(1-alp_p)) \
             +np.sign(z)*spc.ellipk(alp1)*spc.ellipeinc(bta1, np.sqrt(1-alp)) \
             -np.sign(z+h)*spc.ellipk(alp2)*spc.ellipeinc(bta2, np.sqrt(1-alp_p)) \
             -np.sign(z)*spc.ellipk(alp1)*spc.ellipkinc(bta1, np.sqrt(1-alp)) \
             +np.sign(z+h)*spc.ellipk(alp2)*spc.ellipkinc(bta2, np.sqrt(1-alp_p))
    k1 = np.sqrt((4*a*r)/(z**2+(a+r)**2))
    k2 = np.sqrt((4*a*r)/(z_p**2+(a+r)**2))
    phi = np.arccos(x/r)
    u_z = 1-(2/np.pi)*(spc.ellipe(alp1)*spc.ellipkinc(bta1, np.sqrt(1-alp)) \
          +spc.ellipk(alp1)*spc.ellipeinc(bta1, np.sqrt(1-alp)) \
          -spc.ellipk(alp1)*spc.ellipkinc(bta1, np.sqrt(1-alp)))
    u_zp = 1-(2/np.pi)*(spc.ellipe(alp2)*spc.ellipkinc(bta2, np.sqrt(1-alp_p)) \
          +spc.ellipk(alp2)*spc.ellipeinc(bta2, np.sqrt(1-alp_p)) \
          -spc.ellipk(alp2)*spc.ellipkinc(bta2, np.sqrt(1-alp_p)))
    bta1_p = np.arcsin(abs(z)/np.sqrt((z**2)+(a-r)**2))
    bta1_pp = np.arcsin(abs(z+h)/np.sqrt(((z+h)**2)+(a-r)**2))
    min_max = []
    for i in np.arange(len(r)):
        min_max.append(min(a,r[i])/(2*max(a,r[i])))
         
    w_z = abs(z)*spc.ellipe(k1)/(np.pi*k1*np.sqrt(a*r)) \
          -(abs(z)*k1*(a**2+r**2+0.5*z**2)*spc.ellipk(k1))/(2*np.pi*((a*r)**(1.5))) \
          +(abs(a**2-r**2)/(2*np.pi*a*r))*( \
          spc.ellipe(k1)*spc.ellipkinc(bta1_p, np.sqrt(1-k1**2)) \
          +spc.ellipk(k1)*spc.ellipeinc(bta1_p, np.sqrt(1-k1**2)) \
          -spc.ellipk(k1)*spc.ellipkinc(bta1_p, np.sqrt(1-k1**2))) \
          +min_max
    w_zp = abs(z+h)*spc.ellipe(k2)/(np.pi*k2*np.sqrt(a*r)) \
          -(abs(z+h)*k2*(a**2+r**2+0.5*(z+h)**2)*spc.ellipk(k2))/(2*np.pi*((a*r)**(1.5))) \
          +(abs(a**2-r**2)/(2*np.pi*a*r))*( \
          spc.ellipe(k2)*spc.ellipkinc(bta1_pp, np.sqrt(1-k2**2)) \
          +spc.ellipk(k1)*spc.ellipeinc(bta1_pp, np.sqrt(1-k2**2)) \
          -spc.ellipk(k1)*spc.ellipkinc(bta1_pp, np.sqrt(1-k2**2))) \
          +min_max
    w_h =  abs(z+h)*spc.ellipe(k2)/(np.pi*k2*np.sqrt(a*r)) \
          -(abs(z+h)*k2*(a**2+r**2+0.5*(z+h)**2)*spc.ellipk(k2))/(2*np.pi*((a*r)**(1.5))) \
          +(abs(a**2-r**2)/(2*np.pi*a*r))*( \
          spc.ellipe(k2)*spc.ellipkinc(bta1_pp, np.sqrt(1-k2**2)) \
          +spc.ellipk(k1)*spc.ellipeinc(bta1_pp, np.sqrt(1-k2**2)) \
          -spc.ellipk(k1)*spc.ellipkinc(bta1_pp, np.sqrt(1-k2**2))) \
          +min_max
    u_h = 1-(2/np.pi)*(spc.ellipe(alp2)*spc.ellipkinc(bta2, np.sqrt(1-alp_p)) \
          +spc.ellipk(alp2)*spc.ellipeinc(bta2, np.sqrt(1-alp_p)) \
          -spc.ellipk(alp2)*spc.ellipkinc(bta2, np.sqrt(1-alp_p)))
    def part(a):
        """ part of Hxr function """
        if np.any(a < r):
            the_result = 2*np.pi*((a/r)**2)*m*np.cos(phi)
        elif np.any(a == r):
            the_result = 0
        else:
            the_result = -2*np.pi*m*np.cos(phi)
        return the_result
    
    H_zz = -4*m*jacobi - 4*np.pi*m*heaviside(z)
    H_zr = 4*np.sqrt(a/r)*m*((1/k1)*((1-0.5*k1**2)*spc.ellipk(k1)-spc.ellipe(k1)) \
           -(1/k2)*((1-0.5*k2**2)*spc.ellipk(k2)-spc.ellipe(k2)))
    H_zx = H_zr*np.cos(phi)
    H_zy = H_zr*np.sin(phi)
    #now for in-plane magnetised cylender ferromagnet
    if (np.any(z>0)) or (np.any(z)<(-h)):
        H_xr = -2*np.pi*a*m*np.cos(phi)*( \
               ((np.sign(z)*u_z-np.sign(z+h)*u_zp)/a) \
               +((np.sign(z)*w_z-np.sign(z+h)*w_zp)/r))
        H_xphi = 2*np.pi*a*m*np.sin(phi)*((np.sign(z)*w_z-np.sign(z+h)*w_zp)/r)
        H_xz = 4*np.cos(phi)*np.sqrt(a/r)*m*((1/k1)*((1-0.5*k1**2)*spc.ellipk(k1)-spc.ellipe(k1)) \
               -(1/k2)*((1-0.5*k2**2)*spc.ellipk(k2)-spc.ellipe(k2)))
    else:
        H_xr = 2*np.pi*a*m*np.cos(phi)*(((u_z+u_zp)/a)-((w_z+w_zp)/r))+part(a)
        H_xphi = (2*np.pi*a*m*np.sin(phi)/r)*(min(a,r)/max(a,r)) \
                 -(2*np.pi*a*m*np.sin(phi)/r)*(w_z+w_zp)
        H_xz = 4*np.cos(phi)*np.sqrt(a/r)*m*((1/k1)*((1-0.5*k1**2)*spc.ellipk(k1)-spc.ellipe(k1)) \
                -(1/k2)*((1-0.5*k2**2)*spc.ellipk(k2)-spc.ellipe(k2)))
     
    H_xx = H_xr*np.cos(phi)-H_xphi*np.sin(phi)
    H_xy = H_xr*np.sin(phi)+H_xphi*np.cos(phi)
    
    Hx = H_zx*np.cos(theta)+H_xx*np.sin(theta)
    Hy = H_zy*np.cos(theta)+H_xy*np.sin(theta)
    Hz = H_zz*np.cos(theta)+H_xz*np.sin(theta)

    return Hx,Hy,Hz