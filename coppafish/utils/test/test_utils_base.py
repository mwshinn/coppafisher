import itertools
import numpy as np

from coppafish.utils import base


def test_to_deep_convert():
    assert base.deep_convert(list()) == tuple()
    assert base.deep_convert([[0, 2, 3], [1, 4], []]) == ((0, 2, 3), (1, 4), tuple())
    assert base.deep_convert(([0, 2, 3], [1, 4], [])) == ((0, 2, 3), (1, 4), tuple())
    assert base.deep_convert([[0, 2, [0]], [1, 4], []]) == ((0, 2, (0,)), (1, 4), tuple())
    assert base.deep_convert([[0, 2, (0,)], [1, 4], []]) == ((0, 2, (0,)), (1, 4), tuple())
    assert base.deep_convert([["fg" * 400], ["a" * 300]]) == (("fg" * 400,), ("a" * 300,))
    assert base.deep_convert(((0, 1), (0,)), list) == [[0, 1], [0]]
    assert base.deep_convert([], list) == []
    assert base.deep_convert([], tuple) == tuple()


def test_get_function_name():
    assert base.get_function_name() == "test_get_function_name"


def test_reed_solomon_codes():
    n_channels_try = [3, 4]
    n_rounds_try = [3, 4, 5, 6]
    for n_channels, n_rounds in itertools.product(n_channels_try, n_rounds_try):
        codes = base.reed_solomon_codes(4, n_rounds, n_channels)
        assert len(codes) == len(set(codes)), "All reed solomon codes must be unique"


def test_round_any():
    assert np.allclose(base.round_any(100.0, 150.0, round_type="round"), 150.0)
    assert np.allclose(base.round_any(0.1, 100.0, round_type="ceil"), 100.0)
    assert np.allclose(base.round_any(0.1, 100.0, round_type="floor"), 0.0)
    # np.ndarray tests
    a = np.array([0.1, 100.0, 150.0])
    assert np.allclose(base.round_any(a, 100.0, round_type="round"), np.array([0.0, 100.0, 200.0]))
    assert np.allclose(base.round_any(a, 101.0, round_type="ceil"), np.array([101.0, 101.0, 202.0]))
    assert np.allclose(base.round_any(a, 101.0, round_type="floor"), np.array([0.0, 0.0, 101.0]))


def test_setdiff2d():
    n_elements = 100
    n_element_size = 10
    rng = np.random.RandomState(20)
    arr1 = rng.rand(n_elements, n_element_size)
    arr2 = np.empty((0, n_element_size))
    output = base.setdiff2d(arr1, arr2)
    # We sort results in ascending order to make sure all the elements are there
    assert np.allclose(np.sort(output, axis=0), np.sort(arr1, axis=0))
    # If true, copy element in arr1 into arr2
    copies = rng.randint(2, size=(n_elements), dtype=bool)
    arr2 = np.append(arr2, arr1[copies], axis=0)
    arr2 = np.append(arr2, rng.rand(n_elements, n_element_size) * 2 + 5, axis=0)
    output = base.setdiff2d(arr1, arr2)
    assert np.allclose(np.sort(output, axis=0), np.sort(arr1[~copies], axis=0))


def test_expand_channels():
    rng = np.random.RandomState(0)
    array = rng.rand(1, 2, 2, 5, 6, 3)
    use_channels = [6, 2, 1]
    not_use_channels = [0, 3, 4, 5]
    n_channels = 7
    output = base.expand_channels(array=array, use_channels=use_channels, n_channels=n_channels)
    assert output.shape == (*array.shape[:-1], n_channels), "Unexpected output shape"
    for i, c in enumerate(use_channels):
        assert np.allclose(output[..., c], array[..., i]), "Unexpected output"
    assert np.allclose(
        output[..., not_use_channels], 0
    ), "Expected zeroes in the new expanded channels that were not assigned"
    assert np.allclose(base.expand_channels(array, [], 5), 0), "Expected all zeroes"
