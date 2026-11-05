"""nnU-Net 2.8.1 E2 variants: the E1 settings (seed 42, a checkpoint every epoch) on the E2 dataset."""

import random
import numpy as np
import torch

from nnunetv2.training.nnUNetTrainer.variants.training_length.nnUNetTrainer_Xepochs import (
    nnUNetTrainer_5epochs, nnUNetTrainer_100epochs,
)


class nnUNetTrainer_E2Smoke(nnUNetTrainer_5epochs):
    def __init__(self, plans, configuration, fold, dataset_json, device=torch.device("cuda")):
        random.seed(42)
        np.random.seed(42)
        torch.manual_seed(42)
        super().__init__(plans, configuration, fold, dataset_json, device)
        self.save_every = 1


class nnUNetTrainer_E2Preliminary(nnUNetTrainer_100epochs):
    def __init__(self, plans, configuration, fold, dataset_json, device=torch.device("cuda")):
        random.seed(42)
        np.random.seed(42)
        torch.manual_seed(42)
        super().__init__(plans, configuration, fold, dataset_json, device)
        self.save_every = 1
