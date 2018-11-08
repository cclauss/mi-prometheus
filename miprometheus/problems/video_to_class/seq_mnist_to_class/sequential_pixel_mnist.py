#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (C) IBM Corporation 2018
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""sequential_pixel_mnist.py: loads the `MNIST` dataset using ``torchvision`` and\
 transform it to a sequence of pixels."""
__author__ = "Younes Bouhadjar & Vincent Marois"

import torch
from torchvision import datasets, transforms

from miprometheus.utils.data_dict import DataDict
from miprometheus.problems.video_to_class.video_to_class_problem import VideoToClassProblem


class SequentialPixelMNIST(VideoToClassProblem):
    """
    The Sequential MNIST implies that the model does not get to see/generate the whole image at once \
    (like for example a normal 2d-ConvNet would), but only one pixel at a time sequentially.

    .. warning::

        The dataset is not originally split into a training set, validation set and test set; only\
        training and test set. It is recommended to use a validation set.

        ``torch.utils.data.SubsetRandomSampler`` is recommended.

    """

    def __init__(self, params):
        """
        Initializes SequentialPixelMNIST problem:

            - Calls ``problems.problem.VideoToClassProblem`` class constructor,
            - Sets following attributes using the provided ``params``:

                - ``self.root_dir`` (`string`) : Root directory of dataset where ``processed/training.pt``\
                    and  ``processed/test.pt`` will be saved,
                - ``self.use_train_data`` (`bool`, `optional`) : If True, creates dataset from ``training.pt``,\
                    otherwise from ``test.pt``
                - ``self.defaut_values`` :

                    >>> self.default_values = {'nb_classes': 10,
                    >>>                        'length': 28*28}

                - ``self.data_definitions`` :

                    >>> self.data_definitions = {'images': {'size': [-1, 28*28, 1, 1, 1], 'type': [torch.Tensor]},
                    >>>             'mask': {'size': [-1, 28*28, 1], 'type': [torch.Tensor]},
                    >>>             'targets': {'size': [-1, 28*28, 1], 'type': [torch.Tensor]},
                    >>>             'targets_label': {'size': [-1, 1], 'type': [list, str]}
                    >>>             }

        :param params: Dictionary of parameters (read from configuration ``.yaml`` file).

        """
        # Call base class constructors.
        super(SequentialPixelMNIST, self).__init__(params)

        # Retrieve parameters from the dictionary.
        self.use_train_data = params['use_train_data']
        self.root_dir = params['root_dir']

        self.num_rows = 28
        self.num_columns = 28

        # define the default_values dict: holds parameters values that a model may need.
        self.default_values = {'nb_classes': 10,
                               'length': 28*28
                               }

        self.data_definitions = {'images': {'size': [-1, 28*28, 1, 1, 1], 'type': [torch.Tensor]},
                                 'mask': {'size': [-1, 28*28, 1], 'type': [torch.Tensor]},
                                 'targets': {'size': [-1, 28*28, 1], 'type': [torch.Tensor]},
                                 'targets_label': {'size': [-1, 1], 'type': [list, str]}
                                 }

        self.name = 'SequentialPixelMNIST'

        # define transforms
        transform = transforms.Compose([transforms.ToTensor(),
                                        transforms.Lambda(lambda x: x.view(-1))])

        # load the dataset
        self.dataset = datasets.MNIST(self.root_dir, train=self.use_train_data,
                                       download=True, transform=transform)

        # Class names.
        self.labels = 'Zero One Two Three Four Five Six Seven Eight Nine'.split(' ')

        self.length = len(self.dataset)

    def __getitem__(self, index):
        """
        Getter method to access the dataset and return a sample.

        :param index: index of the sample to return.
        :type index: int

        :return: ``DataDict({'images', 'mask', 'targets', 'targets_label'})``, with:

            - images: sequence of 'images' in [batch size, sequence length, channels, x, y] format. Single pixels, so x == y == 1
            - mask
            - targets: Index of the target class

        """
        # get sample
        img, target = self.dataset.__getitem__(index)

        # get label
        label = self.labels[target.data]

        # create mask
        mask = torch.zeros((self.num_rows * self.num_columns,1)).type(self.app_state.IntTensor)
        mask[-1, 0] = 1

        data_dict = DataDict({key: None for key in self.data_definitions.keys()})
        data_dict['images'] = img.view(28*28,1,1,1)
        data_dict['mask'] = mask
        data_dict['targets'] = target*torch.ones((28*28,1),dtype=torch.long)
        data_dict['targets_label'] = label

        return data_dict

    def collate_fn(self, batch):
        """
        Combines a list of ``DataDict`` (retrieved with ``__getitem__`` ) into a batch.

        .. note::

            This function wraps a call to ``default_collate`` and simply returns the batch as a ``DataDict``\
            instead of a dict.
            Multi-processing is supported as the data sources are small enough to be kept in memory\
            (`training.pt` has a size of 47.5 MB).

        :param batch: list of individual ``DataDict`` samples to combine.

        :return: ``DataDict({'sequences','targets', 'targets_label'})`` containing the batch.

        """

        return DataDict({key: value for key, value in zip(self.data_definitions.keys(),
                                                          super(SequentialPixelMNIST, self).collate_fn(batch).values())})


if __name__ == "__main__":
    """ Tests sequence generator - generates and displays a random sample"""

    # Load parameters.
    from miprometheus.utils.param_interface import ParamInterface
    params = ParamInterface()
    params.add_default_params({'use_train_data': True, 'root_dir': '~/data/mnist'})

    batch_size = 64

    # Create problem.
    problem = SequentialPixelMNIST(params)

    # get a sample
    sample = problem[0]
    print(repr(sample))

    # test whether data structures match expected definitions
    # images should be (batch size x sequence x channel x height x width)
    # as this is a sample, we should have (sequence x channel x height x width) == (28*28, 1, 1, 1)
    assert sample['images'].shape == torch.ones((28*28, 1, 1, 1)).shape, "Unit test failed! Expected images shape {} but got {}".format(torch.ones((28*28, 1, 1, 1)).shape, sample['images'].shape)

    # mask should be (sequence x class) == (28*28, 1)
    assert sample['mask'].shape == torch.ones((28*28,1)).shape, "Unit test failed! Expected mask shape {} but got {}".format(torch.ones((28*28,1)).shape, sample['mask'].shape)

    # targets should be (sequence x class) == (28*28, 1)
    assert sample['targets'].shape == torch.ones((28*28,1)).shape, "Unit test failed! Expected targets shape {} but got {}".format(torch.ones((28*28,1)).shape, sample['targets'].shape)

    # targets_label should be (class) == (1)
    assert type(sample['targets_label']) == type(' ') , "Unit test failed! Expected target_labels to be str but got {}".format(type(sample['targets_label']))

    print('__getitem__ works.')

    # wrap DataLoader on top of this Dataset subclass
    from torch.utils.data import DataLoader

    dataloader = DataLoader(dataset=problem, collate_fn=problem.collate_fn,
                            batch_size=batch_size, shuffle=True, num_workers=8)

    # try to see if there is a speed up when generating batches w/ multiple workers
    import time

    s = time.time()
    for i, batch in enumerate(dataloader):
        print('Batch # {} - {}'.format(i, type(batch)))

    print('Number of workers: {}'.format(dataloader.num_workers))
    print('time taken to exhaust the dataset for a batch size of {}: {}s'.format(batch_size, time.time() - s))

    # Get a single batch from data loader
    batch = next(iter(dataloader))    
   
    # reshape image for display. In sequential mnist each sequence has 28*28 entries of one pixel value. We will go from a 28*28-long sequence of single pixels of a 1-long sequence of a full image (28x28).
    batch['images'] = batch['images'].view(batch_size,1,1,problem.num_columns,problem.num_rows)

    problem.show_sample(batch, 0)

    print('Unit test completed')
