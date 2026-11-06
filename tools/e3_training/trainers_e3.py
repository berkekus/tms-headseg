"""Dataset003 E3: standard nnU-Net sampling/loss, seed 42, checkpoint each epoch."""

import random
import numpy as np
import torch
from nnunetv2.training.nnUNetTrainer.variants.training_length.nnUNetTrainer_Xepochs import nnUNetTrainer_100epochs


class nnUNetTrainer_E3Preliminary(nnUNetTrainer_100epochs):
    def __init__(self, plans, configuration, fold, dataset_json, device=torch.device("cuda")):
        if configuration != "3d_fullres" or str(fold) != "0" or dataset_json.get("labels", {}).get("ignore") != 6:
            raise ValueError("E3 requires 3d_fullres, fixed fold 0 and ignore label 6.")
        random.seed(42)
        np.random.seed(42)
        torch.manual_seed(42)
        super().__init__(plans, configuration, fold, dataset_json, device)
        self.save_every = 1


class nnUNetTrainer_E3Smoke(nnUNetTrainer_E3Preliminary):
    def __init__(self, plans, configuration, fold, dataset_json, device=torch.device("cuda")):
        super().__init__(plans, configuration, fold, dataset_json, device)
        self.num_epochs = 5
