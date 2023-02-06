import numpy as np
import scipy as sp
from scipy import special
import ctypes

lib = ctypes.cdll.LoadLibrary("./libsphericart.so")

c_prefactors = lib.compute_sph_prefactors
c_prefactors.restype = None
c_prefactors.argtypes = [
    ctypes.c_uint,
    ctypes.POINTER(ctypes.c_double),
]

c_spherical_harmonics = lib.cartesian_spherical_harmonics_cache
c_spherical_harmonics.restype = None
c_spherical_harmonics.argtypes = [
    ctypes.c_uint,
    ctypes.c_uint,
    ctypes.POINTER(ctypes.c_double),
    ctypes.POINTER(ctypes.c_double),
    ctypes.POINTER(ctypes.c_double),
    ctypes.POINTER(ctypes.c_double),
]

def get_prefactors(l_max):
    prefactors = np.empty((l_max+1)*(l_max+2)//2)
    prefactors_ptr = prefactors.ctypes.data_as(ctypes.POINTER(ctypes.c_double))
    c_prefactors(l_max, prefactors_ptr)
    return prefactors

def spherical_harmonics(l_max, xyz, prefactors, gradients=False):
    n_samples = xyz.shape[0]
    sph = np.empty((n_samples, (l_max+1)**2))
    prefactors_ptr = prefactors.ctypes.data_as(ctypes.POINTER(ctypes.c_double))
    xyz_ptr = xyz.ctypes.data_as(ctypes.POINTER(ctypes.c_double))
    sph_ptr = sph.ctypes.data_as(ctypes.POINTER(ctypes.c_double))
    if gradients:
        pass  # allocate gradients and create pointer to them
    else:
        dsph_ptr = ctypes.POINTER(ctypes.c_double)()
    c_spherical_harmonics(n_samples, l_max, prefactors_ptr, xyz_ptr, sph_ptr, dsph_ptr)
    return sph


def test_against_scipy(xyz: np.ndarray, l: int, m: int):

    # Scipy spherical harmonics:
    # Note: scipy's theta and phi are the opposite of those in our convention
    x = xyz[:, 0]
    y = xyz[:, 1]
    z = xyz[:, 2]
    r = np.sqrt(x**2+y**2+z**2)
    theta = np.arccos(z/r)
    phi = np.arctan2(y, x)
    complex_sh_scipy_l_m = sp.special.sph_harm(m, l, phi, theta)
    complex_sh_scipy_l_negm = sp.special.sph_harm(-m, l, phi, theta)

    if m > 0:
        sh_scipy_l_m = ((complex_sh_scipy_l_negm+(-1)**m*complex_sh_scipy_l_m)/np.sqrt(2.0)).real
    elif m < 0:
        sh_scipy_l_m = ((-complex_sh_scipy_l_m+(-1)**m*complex_sh_scipy_l_negm)/np.sqrt(2.0)).imag
    else: # m == 0
        sh_scipy_l_m = complex_sh_scipy_l_m.real

    prefactors = get_prefactors(l_max)
    sh_sphericart = spherical_harmonics(l_max, xyz, prefactors, gradients=False)
    sh_sphericart_l_m = sh_sphericart[:, l*l+l+m] / r**l

    assert np.allclose(sh_scipy_l_m, sh_sphericart_l_m), f"assertion failed for l={l}, m={m}"


n_samples = 10000
l_max = 10
xyz = np.random.rand(n_samples, 3)
for l in range(0, l_max+1):
    for m in range(-l, l+1):
        test_against_scipy(xyz, l, m)

print("Assertions passed successfully!")


n_tries = 100
import time
prefactors = get_prefactors(l_max)
start = time.time()
for _ in range(100):
    sh_sphericart = spherical_harmonics(l_max, xyz, prefactors, gradients=False)
finish = time.time()
print(f"We took {1000*(finish-start)/n_tries} ms")

import torch
import e3nn
xyz = torch.tensor(xyz)
sh = e3nn.o3.spherical_harmonics(l_max, xyz, normalize=False)  # allow compilation (??)
start = time.time()
for _ in range(100):
    sh = e3nn.o3.spherical_harmonics(l_max, xyz, normalize=False)
finish = time.time()
print(f"e3nn took {1000*(finish-start)/n_tries} ms")

