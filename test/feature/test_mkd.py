import pytest
import kornia.testing as utils  # test utils

from torch.testing import assert_allclose
from torch.autograd import gradcheck
from kornia.feature.mkd import *


@pytest.mark.parametrize("ps", [5, 13, 25])
def test_get_grid_dict(ps):
    grid_dict = get_grid_dict(ps)
    param_keys = ['x','y','phi','rho']
    assert set(grid_dict.keys()) == set(param_keys)
    for k in param_keys:
        assert grid_dict[k].shape == (ps, ps)


@pytest.mark.parametrize("d1,d2",
                         [(1, 1), (1,2), (2,1), (5,6)])
def test_get_kron_order(d1,d2):
    out = get_kron_order(d1, d2)
    assert out.shape == (d1 * d2, 2)

class TestMKDGradients:
    @pytest.mark.parametrize("ps", [5, 13, 25])
    def test_shape(self, ps, device):
        inp = torch.ones(1, 1, ps, ps, device=device)
        gradients = MKDGradients().to(device)
        out = gradients(inp)
        assert out.shape == (1, 2, ps, ps)

    @pytest.mark.parametrize("bs", [1, 5, 13])
    def test_batch_shape(self, bs, device):
        inp = torch.ones(bs, 1, 15, 15, device=device)
        gradients = MKDGradients().to(device)
        out = gradients(inp)
        assert out.shape == (bs, 2, 15, 15)

    def test_print(self, device):
        gradients = MKDGradients().to(device)
        gradients.__repr__()

    def test_toy(self, device):
        patch = torch.ones(1, 1, 6, 6, device=device).float()
        patch[0, 0, :, 3:] = 0
        gradients = MKDGradients().to(device)
        out = gradients(patch)
        expected = torch.Tensor([0, 0, 1., 1., 0, 0], device=device)
        expected_mags = expected.unsqueeze(0).repeat(6,1)
        expected_oris = expected_mags * 0
        assert_allclose(out[0,0,:,:], expected_mags, atol=1e-3, rtol=1e-3)
        assert_allclose(out[0,1,:,:], expected_oris, atol=1e-3, rtol=1e-3)

    def test_gradcheck(self, device):
        batch_size, channels, height, width = 1, 1, 13, 13
        patches = torch.rand(batch_size, channels, height, width, device=device)
        patches = utils.tensor_to_gradcheck_var(patches)  # to var

        def grad_describe(patches):
            return MKDGradients()(patches)
        assert gradcheck(grad_describe, (patches),
                         raise_exception = True, nondet_tol = 1e-4)

class TestVonMisesKernel:
    @ pytest.mark.parametrize("ps", [5, 13, 25])
    def test_shape(self, ps, device):
        inp=torch.ones(1, 1, ps, ps, device = device)
        vm=VonMisesKernel(patch_size = ps,
                            coeffs = [0.38214156, 0.48090413]).to(device)
        out=vm(inp)
        assert out.shape == (1, 3, ps, ps)

    @ pytest.mark.parametrize("bs", [1, 5, 13])
    def test_batch_shape(self, bs, device):
        inp=torch.ones(bs, 1, 15, 15, device = device)
        vm=VonMisesKernel(patch_size = 15,
                            coeffs = [0.38214156, 0.48090413]).to(device)
        out=vm(inp)
        assert out.shape == (bs, 3, 15, 15)

    @ pytest.mark.parametrize("coeffs", COEFFS.values())
    def test_coeffs(self, coeffs, device):
        inp=torch.ones(1, 1, 15, 15, device = device)
        vm=VonMisesKernel(patch_size = 15,
                          coeffs=coeffs).to(device)
        out = vm(inp)
        assert out.shape == (1, 2 * len(coeffs) - 1, 15, 15)

    def test_print(self, device):
        vm = VonMisesKernel(patch_size=32,
                          coeffs=[0.38214156, 0.48090413]).to(device)
        vm.__repr__()

    def test_toy(self, device):
        patch = torch.ones(1, 1, 6, 6, device=device).float()
        patch[0, 0, :, 3:] = 0
        vm = VonMisesKernel(patch_size=6,
                          coeffs=[0.38214156, 0.48090413]).to(device)
        out = vm(patch)
        expected = torch.ones_like(out[0,0,:,:], device=device)
        assert_allclose(out[0,0,:,:], expected * 0.6182, atol=1e-3, rtol=1e-3)

        expected = torch.Tensor([0.3747, 0.3747, 0.3747,
                               0.6935, 0.6935, 0.6935], device=device)
        expected = expected.unsqueeze(0).repeat(6,1)
        assert_allclose(out[0,1,:,:], expected, atol=1e-3, rtol=1e-3)

        expected = torch.Tensor([0.5835, 0.5835, 0.5835,
                               0.0000, 0.0000, 0.0000], device=device)
        expected = expected.unsqueeze(0).repeat(6,1)
        assert_allclose(out[0,2,:,:], expected, atol=1e-3, rtol=1e-3)

    def test_gradcheck(self, device):
        batch_size, channels, ps = 1, 1, 13
        patches = torch.rand(batch_size, channels, ps, ps, device=device)
        patches = utils.tensor_to_gradcheck_var(patches)  # to var

        def vm_describe(patches, ps=13):
            return VonMisesKernel(patch_size=ps,
                  coeffs=[0.38214156, 0.48090413]).double()(patches.double())
        assert gradcheck(vm_describe, (patches, ps),
                         raise_exception=True, nondet_tol=1e-4)



class TestEmbedGradients:

    @pytest.mark.parametrize("ps,relative", [(5, True), (13, True), (25, True),
      (5, False), (13, False), (25, False)])
    def test_shape(self, ps, relative, device):
        inp = torch.ones(1, 2, ps, ps, device=device)
        emb_grads = EmbedGradients(patch_size=ps,
                            relative=relative).to(device)
        out = emb_grads(inp)
        assert out.shape == (1, 7, ps, ps)

    @pytest.mark.parametrize("bs", [1, 5, 13])
    def test_batch_shape(self, bs, device):
        inp = torch.ones(bs, 2, 15, 15, device=device)
        emb_grads = EmbedGradients(patch_size=15,
                            relative=True).to(device)
        out = emb_grads(inp)
        assert out.shape == (bs, 7, 15, 15)

    def test_print(self, device):
        emb_grads = EmbedGradients(patch_size=15,
                            relative=True).to(device)
        emb_grads.__repr__()

    def test_toy(self, device):
        grads = torch.ones(1, 2, 6, 6, device=device).float()
        grads[0, 0, :, 3:] = 0
        emb_grads = EmbedGradients(patch_size=6,
                            relative=True).to(device)
        out = emb_grads(grads)
        expected = torch.ones_like(out[0,0,:,:3], device=device)
        assert_allclose(out[0,0,:,:3], expected * .3787, atol=1e-3, rtol=1e-3)
        assert_allclose(out[0,0,:,3:], expected * 0, atol=1e-3, rtol=1e-3)

    def test_gradcheck(self, device):
        batch_size, channels, ps = 1, 2, 13
        patches = torch.rand(batch_size, channels, ps, ps, device=device)
        patches = utils.tensor_to_gradcheck_var(patches)  # to var

        def emb_grads_describe(patches, ps=13):
            return EmbedGradients(patch_size=ps,
                          relative=True).double()(patches.double())
        assert gradcheck(emb_grads_describe, (patches, ps),
                         raise_exception=True, nondet_tol=1e-4)