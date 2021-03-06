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

"""video_to_class_problem.py: abstract base class for sequential vision problems."""
__author__ = "Tomasz Kornuta, Younes Bouhadjar, Vincent Marois"
import torch
import torch.nn as nn
import numpy as np
from miprometheus.problems.problem import Problem


class VideoToClassProblem(Problem):
    """
    Abstract base class for sequential vision problems.

    Problem classes like Sequential MNIST inherits from it.

    Provides some basic features useful in all problems of such type.

    """

    def __init__(self, params):
        """
        Initializes problem:

            - Calls ``problems.problem.Problem`` class constructor,
            - Sets loss function to ``CrossEntropy``,
            - sets ``self.data_definitions`` to:

                >>> self.data_definitions = {'images': {'size': [-1, -1, 3, -1, -1], 'type': [torch.Tensor]},
                >>>                          'mask': {'size': [-1, -1, -1], 'type': [torch.Tensor]},
                >>>                          'targets': {'size': [-1, -1, 1], 'type': [torch.Tensor]},
                >>>                          'targets_label': {'size': [-1, 1], 'type': [list, str]}
                >>>                         }

        :param params: Dictionary of parameters (read from configuration ``.yaml`` file).
        """
        super(VideoToClassProblem, self).__init__(params)

        # Set default loss function - cross entropy.
        self.loss_function = nn.CrossEntropyLoss()

        # set default data_definitions dict
	# images = batch size x sequence length x channels x height x width
	# mask = batch size x sequence length x class
	# targets = batch size x sequence length x class
	# targets_label = batch size x class
        self.data_definitions = {'images': {'size': [-1,-1, 3, -1, -1], 'type': [torch.Tensor]},
                                 'mask': {'size': [-1, -1, -1], 'type': [torch.Tensor]},
                                 'targets': {'size': [-1, -1, 1], 'type': [torch.Tensor]},
                                 'targets_label': {'size': [-1, 1], 'type': [list, str]}
                                 }

        # "Default" problem name.
        self.name = 'VideoToClassProblem'

    def calculate_accuracy(self, data_dict, logits):
        """
        Calculates accuracy equal to mean number of correct classification in a given batch.

        .. warning::

            Applies a mask to the logits.


        :param logits: Predictions of the model.

        :param data_dict: DataDict containing the targets and the mask.
        :type data_dict: DataDict

        :return: Accuracy.

        """
        # Mask logits (ONLY LOGITS!)
        masked_logits = logits[:, data_dict['mask'], :][:, 0, :]

        # Get the index of the max log-probability.
        pred = masked_logits.max(1, keepdim=True)[1]
        correct = pred.eq(data_dict['targets'].view_as(pred)).sum().item()

        # Calculate the accuracy.
        batch_size = logits.size(0)
        accuracy = correct / batch_size

        return accuracy

    def evaluate_loss(self, data_dict, logits):
        """ Computes loss.

        .. warning::

            Applies a mask to the logits.


        :param logits: Predictions of the model.

        :param data_dict: DataDict containing the targets and the mask.
        :type data_dict: DataDict

        :return: Loss.
        """
        # Mask logits (ONLY LOGITS!)
        masked_logits = logits[:, data_dict['mask'], :][:, 0, :]

        # Compute loss using the provided loss function.
        loss = self.loss_function(masked_logits, data_dict['targets'])

        return loss

    def add_statistics(self, stat_col):
        """
        Add accuracy statistic to ``StatisticsCollector``.

        :param stat_col: ``StatisticsCollector``.

        """
        stat_col.add_statistic('acc', '{:12.10f}')

    def collect_statistics(self, stat_col, data_dict, logits):
        """
        Collects accuracy.

        :param stat_col: ``StatisticsCollector``.

        :param data_dict: DataDict containing the targets and the mask.
        :type data_dict: DataDict

        :param logits: Predictions of the model.

        """
        stat_col['acc'] = self.calculate_accuracy(data_dict, logits)

    def show_sample(self, data_dict, sample_number=0, sequence_number=0):
        """
        Shows a sample from the batch.

        :param data_dict: ``DataDict`` containing inputs and targets.
        :type data_dict: DataDict

        :param sample_number: Number of sample in batch (default: 0)
        :type sample_number: int

	:param sequence_number: Which image in the sequence to display (default: 0)
	:type sequence_number: int

        """
        import matplotlib.pyplot as plt

        # Unpack dict.
        #images, masks, targets, labels = data_dict.values()
        images = data_dict['images']
        # mask = data_dict['mask']
        targets = data_dict['targets']
        labels = data_dict['targets_label']

        # Get sample.
        images = images[sample_number].cpu().detach().numpy()
        targets = targets[sample_number].cpu().detach().numpy()
        label = labels[sample_number]

        # Get image in sequence.
        image = images[sequence_number]
        target = targets[sequence_number]

        # Reshape image.
        if image.shape[0] == 1:
            # This is a single channel image - get rid of this dimension
            image = np.squeeze(image, axis=0)
        else:
            # More channels - move channels to axis2, according to matplotilb documentation.
            # (X : array_like, shape (n, m) or (n, m, 3) or (n, m, 4))
            image = image.transpose(1, 2, 0)

        # show data.
        plt.xlabel('num_columns')
        plt.ylabel('num_rows')
        plt.title('Target class: {} ({}), {}th in Sequence'.format(label, target, sequence_number))
        plt.imshow(image, interpolation='nearest', aspect='auto', cmap='gray_r')

        # Plot!
        plt.show()


if __name__ == '__main__':

    from miprometheus.utils.param_interface import ParamInterface

    sample = VideoToClassProblem(ParamInterface())[0]
    # equivalent to ImageToClassProblem(params={}).__getitem__(index=0)

    print(repr(sample))
