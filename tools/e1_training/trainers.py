"""nnU-Net 2.8.1 E1 variants: seed initialization and save each epoch."""

import random
import numpy as np
import torch

from nnunetv2.training.nnUNetTrainer.variants.training_length.nnUNetTrainer_Xepochs import (
    nnUNetTrainer_5epochs, nnUNetTrainer_100epochs,
)


class nnUNetTrainer_E1Smoke(nnUNetTrainer_5epochs):
    def __init__(self, plans, configuration, fold, dataset_json, device=torch.device("cuda")):
        random.seed(42)
        np.random.seed(42)
        torch.manual_seed(42)
        super().__init__(plans, configuration, fold, dataset_json, device)
        self.save_every = 1


class nnUNetTrainer_E1Preliminary(nnUNetTrainer_100epochs):
    def __init__(self, plans, configuration, fold, dataset_json, device=torch.device("cuda")):
        random.seed(42)
        np.random.seed(42)
        torch.manual_seed(42)
        super().__init__(plans, configuration, fold, dataset_json, device)
        self.save_every = 1
