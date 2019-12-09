import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import axes3d
from h_field_strength import H_spherical_ferromag as H

m = 1       #volume magnetisation
a = 1       #radius of the ferromagnet
h = 1     #thickness of the ferromagnet
theta = np.pi/4 #angle of the magnetisation

value = 1e1
rho = np.array([20 for i in np.arange(value)])
theta0 = np.linspace(0,np.pi,value)
phi0 = np.linspace(0,np.pi*2,value)
x0 = rho*np.sin(theta0)*np.cos(phi0)+1
y0= rho*np.sin(theta0)*np.sin(phi0)+1
z0 = rho*np.cos(theta0)+1


x = []
y = []
z = []
for i in rho:
    for j in theta0:
        for k in phi0:
            x.append(i*np.sin(j)*np.cos(k)+1)
            y.append(i*np.sin(j)*np.sin(k)+1)
            z.append(i*np.cos(j)+1)

hx = H(np.array(x),np.array(y),np.array(z))[0]
hy = H(np.array(x),np.array(y),np.array(z))[1]
hz = H(np.array(x),np.array(y),np.array(z))[2]
x = np.array(x)
y = np.array(y)
z = np.array(z)

fig = plt.figure(dpi = 100)
ax = fig.gca(projection='3d')
xx, yy, zz = np.meshgrid(x0,y0,z0)
ax.quiver(x, y, z, hx, hy, hz, length=1, arrow_length_ratio=0.5,normalize=True,colors=(1,0,1))
plt.show()