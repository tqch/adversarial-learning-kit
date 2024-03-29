import torch.nn as nn


class VGG(nn.Module):
    default_conv_layers_configs = {
        "vgg16": [2, 2, 3, 3, 3],
        "vgg19": [2, 2, 4, 4, 4]
    }

    def __init__(
            self,
            conv_layers_config,
            input_shape=(3, 32, 32),
            n_class=10
    ):
        super(VGG, self).__init__()
        self.conv_layers_config = conv_layers_config
        self.input_shape = input_shape
        self.n_class = n_class

        self.layer1 = self._make_layer(3, 64, self.conv_layers_config[0])
        self.layer2 = self._make_layer(64, 128, self.conv_layers_config[1])
        self.layer3 = self._make_layer(128, 256, self.conv_layers_config[2])
        self.layer4 = self._make_layer(256, 512, self.conv_layers_config[3])
        self.layer5 = self._make_layer(512, 512, self.conv_layers_config[4])

        post_conv_shape = self.input_shape[1] // 2 ** 5, self.input_shape[2] // 2 ** 5
        
        intermediate_dimension = 512\
            if post_conv_shape[0] * post_conv_shape[1] == 1 else 4096

        self.classifier = nn.Sequential(
            nn.Flatten(start_dim=1),
            nn.Linear(post_conv_shape[0] * post_conv_shape[1] * 512, 4096),
            nn.Dropout(0.5),
            nn.ReLU(inplace=True),
            nn.Linear(intermediate_dimension, intermediate_dimension),
            nn.Dropout(0.5),
            nn.ReLU(inplace=True),
            nn.Linear(intermediate_dimension, self.n_class)
        )

    @staticmethod
    def _make_layer(in_channels, out_channels, n_layers):
        layers = []
        layers.append(nn.Conv2d(in_channels, out_channels, 3, 1, 1, bias=False))
        layers.append(nn.BatchNorm2d(out_channels))
        layers.append(nn.ReLU(inplace=True))

        for i in range(n_layers - 1):
            layers.append(nn.Conv2d(out_channels, out_channels, 3, 1, 1, bias=False))
            layers.append(nn.BatchNorm2d(out_channels))
            layers.append(nn.ReLU(inplace=True))

        layers.append(nn.MaxPool2d(2))

        return nn.Sequential(*layers)

    def forward(self, x):
        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.layer4(x)
        x = self.layer5(x)
        x = self.classifier(x)

        return x

    @staticmethod
    def from_default_config(model_type, input_shape=(3, 32, 32), n_class=10):
        return VGG(
            conv_layers_config=VGG.default_conv_layers_configs[model_type],
            input_shape=input_shape,
            n_class=n_class
        )


if __name__ == "__main__":
    import os
    from advkit.utils.models import *
    from advkit.utils.data import get_dataloader
    from torch.optim import SGD, lr_scheduler

    ROOT = os.path.expanduser("~/advkit")
    DATA_PATH = os.path.join(ROOT, "datasets")
    CHECKPOINT_PATH = os.path.join(ROOT, "checkpoints/cifar10_vgg16.pt")
    TRAIN = not os.path.exists(CHECKPOINT_PATH)
    DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    augmentation = True
    testloader = get_dataloader(dataset="cifar10", root=DATA_PATH, augmentation=augmentation)

    if not TRAIN:
        model = VGG.from_default_config("vgg16")
        model.load_state_dict(torch.load(CHECKPOINT_PATH, map_location=DEVICE)["model_weights"])
        model.to(DEVICE)
        evaluate(model, testloader, device=DEVICE)
    else:
        set_seed(42)
        trainloader = get_dataloader(
            dataset="cifar10",
            root=DATA_PATH,
            train=True,
            train_batch_size=128,
            augmentation=augmentation
        )

        model = VGG.from_default_config("vgg16")
        model.to(DEVICE)
        epochs = 200
        loss_fn = nn.CrossEntropyLoss()
        optimizer = SGD(model.parameters(), **OPTIMIZER_CONFIGS["cifar10"])
        # scheduler = lr_scheduler.ReduceLROnPlateau(optimizer, mode="max", factor=0.1, patience=5)
        scheduler = lr_scheduler.StepLR(optimizer, step_size=100, gamma=0.1)
        best_epoch, best_val_acc = train(
            model,
            epochs,
            trainloader,
            loss_fn,
            optimizer,
            scheduler,
            testloader,
            num_eval_batches=-1,
            checkpoint_path=CHECKPOINT_PATH,
            device=DEVICE
        )

