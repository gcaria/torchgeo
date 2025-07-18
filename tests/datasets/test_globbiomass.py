# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import os
import shutil
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import pytest
import torch
import torch.nn as nn
from pyproj import CRS
from pytest import MonkeyPatch

from torchgeo.datasets import (
    DatasetNotFoundError,
    GlobBiomass,
    IntersectionDataset,
    UnionDataset,
)


class TestGlobBiomass:
    @pytest.fixture
    def dataset(self, monkeypatch: MonkeyPatch, tmp_path: Path) -> GlobBiomass:
        shutil.copy(
            os.path.join('tests', 'data', 'globbiomass', 'N00E020_agb.zip'), tmp_path
        )
        shutil.copy(
            os.path.join('tests', 'data', 'globbiomass', 'N00E020_gsv.zip'), tmp_path
        )

        md5s = {
            'N00E020_agb.zip': '22e11817ede672a2a76b8a5588bc4bf4',
            'N00E020_gsv.zip': 'e79bf051ac5d659cb21c566c53ce7b98',
        }

        monkeypatch.setattr(GlobBiomass, 'md5s', md5s)
        root = tmp_path
        transforms = nn.Identity()
        return GlobBiomass(root, transforms=transforms, checksum=True)

    def test_getitem(self, dataset: GlobBiomass) -> None:
        x = dataset[dataset.bounds]
        assert isinstance(x, dict)
        assert isinstance(x['crs'], CRS)
        assert isinstance(x['mask'], torch.Tensor)

    def test_len(self, dataset: GlobBiomass) -> None:
        assert len(dataset) == 1

    def test_already_extracted(self, dataset: GlobBiomass) -> None:
        GlobBiomass(dataset.paths)

    def test_not_downloaded(self, tmp_path: Path) -> None:
        with pytest.raises(DatasetNotFoundError, match='Dataset not found'):
            GlobBiomass(tmp_path, checksum=True)

    def test_corrupted(self, tmp_path: Path) -> None:
        with open(os.path.join(tmp_path, 'N00E020_agb.zip'), 'w') as f:
            f.write('bad')
        with pytest.raises(RuntimeError, match='Dataset found, but corrupted.'):
            GlobBiomass(tmp_path, checksum=True)

    def test_and(self, dataset: GlobBiomass) -> None:
        ds = dataset & dataset
        assert isinstance(ds, IntersectionDataset)

    def test_or(self, dataset: GlobBiomass) -> None:
        ds = dataset | dataset
        assert isinstance(ds, UnionDataset)

    def test_plot(self, dataset: GlobBiomass) -> None:
        query = dataset.bounds
        x = dataset[query]
        dataset.plot(x, suptitle='Test')
        plt.close()

    def test_plot_prediction(self, dataset: GlobBiomass) -> None:
        query = dataset.bounds
        x = dataset[query]
        x['prediction'] = x['mask'].clone()
        dataset.plot(x, suptitle='Prediction')
        plt.close()

    def test_invalid_query(self, dataset: GlobBiomass) -> None:
        with pytest.raises(
            IndexError, match='query: .* not found in index with bounds:'
        ):
            dataset[100:100, 100:100, pd.Timestamp.min : pd.Timestamp.min]
