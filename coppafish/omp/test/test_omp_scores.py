import torch


def test_score_pixel_score_image() -> None:
    from coppafish.omp import scores

    im_y, im_x, im_z = 4, 5, 6
    spot_shape = 1, 3, 5

    coefficient_image = torch.zeros((2, im_y, im_x, im_z), dtype=torch.float32)
    coefficient_image[1, 1, 3, 2] = 0.8
    mean_spot = torch.zeros(spot_shape, dtype=torch.float32)
    mean_spot[0, 1, 2] = 0.5
    mean_spot[0, 2, 2] = 0.9
    mean_spot[0, 1, 3] = 0.1

    scores = scores.score_pixel_score_image(coefficient_image, mean_spot)

    assert scores.shape == coefficient_image.shape
    assert torch.allclose(scores[0], torch.zeros(1).float())
    assert torch.isclose(scores[1, 1, 3, 2], 0.8 * 0.5 / mean_spot.sum())
    assert torch.isclose(scores[1, 0, 0, 0], torch.asarray([0], dtype=torch.float32))
