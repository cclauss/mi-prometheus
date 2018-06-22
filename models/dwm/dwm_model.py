import torch
import logging
import numpy as np

from torch import nn

# Add path to main project directory - so we can test the base plot, saving images, movies etc.
import os, sys
sys.path.append(os.path.join(os.path.dirname(__file__),  '..', '..')) 

from models.sequential_model import SequentialModel
from models.dwm.dwm_cell import DWMCell


class DWM(SequentialModel):
    """Applies a DWM layer to an input sequences - what kind of description is that...? ;) """
    """ @Younes: MODEL DESCRIPTION GOES HERE! really...  """

    def __init__(self, params):

        """"
        Constructor. Initializes parameters on the basis of dictionary of parameters passed as argument.
        :param params: Dictionary of parameters.
        """
        # Call base class initialization.
        super(DWM, self).__init__(params)

        self.in_dim = params["control_bits"] + params["data_bits"]

        try:
            self.output_units  = params['output_bits']
        except KeyError:
            self.output_units = params['data_bits']

        self.state_units =params["hidden_state_dim"]
        self.num_heads = params["num_heads"]
        self.is_cam = params["use_content_addressing"]
        self.num_shift = params["shift_size"]
        self.M = params["memory_content_size"]
        self.memory_addresses_size = params["memory_addresses_size"]
        self.label = params["name"]

        # This is for the time plot
        self.cell_state_history = None

        # Create the DWM components
        self.DWMCell = DWMCell(self.in_dim, self.output_units, self.state_units,
                               self.num_heads, self.is_cam, self.num_shift, self.M)

    def forward(self, data_tuple):
        """
        Forward function

        :param data_tuple** = (inputs, targets)
        :param inputs of shape `(batch, sequence_length, input_size)`: tensor containing the data sequences of the batch.
        :param targets of shape `(batch, sequence_length, output_size)`: tensor containing the target sequences of the batch.

        :returns output of shape `(batch, sequence_length, output_size)`:


        Example:

        >>> dwm = DWM(params)
        >>> inputs = torch.randn(5, 3, 10)
        >>> targets = torch.randn(5, 3, 20)
        >>> data_tuple = (inputs, targets)
        >>> output = dwm(data_tuple)

        """
        # Unpack tuple.
        (inputs, targets) = data_tuple

        if self.app_state.visualize:
            self.cell_state_history = []

        output = None
        # TODO
        if len(inputs.size()) == 4:
            inputs = inputs[:, 0, :, :]

        batch_size = inputs.size(0)
        seq_length = inputs.size(-2)

        # The length of the memory is set to be equal to the input length in case ```self.memory_addresses_size == -1```
        if self.memory_addresses_size == -1:
            if seq_length < self.num_shift:
                memory_addresses_size = self.num_shift  # memory size can't be smaller than num_shift (see circular_convolution implementation)
            else:
                memory_addresses_size = seq_length  # a hack for now
        else:
            memory_addresses_size = self.memory_addresses_size

        # Set type
        dtype = torch.cuda.FloatTensor if inputs.is_cuda else torch.FloatTensor

        # Init state
        cell_state = self.DWMCell.init_state(memory_addresses_size, batch_size, dtype)

        # loop over the different sequences
        for j in range(seq_length):
            output_cell, cell_state = self.DWMCell(inputs[..., j, :], cell_state)

            if output_cell is None:
                continue

            output_cell = output_cell[..., None, :]
            if output is None:
                output = output_cell

            # Concatenate output
            else:
                output = torch.cat([output, output_cell], dim=-2)

            # This is for the time plot
            if self.app_state.visualize:
                self.cell_state_history.append((cell_state.memory_state.detach().numpy(),
                                                cell_state.interface_state.head_weight.detach().numpy(),
                                                cell_state.interface_state.snapshot_weight.detach().numpy()))

        return output

    # Method to change memory size
    def set_memory_size(self, mem_size):
        self.memory_addresses_size = mem_size

    def generate_figure_layout(self):
        from matplotlib.figure import Figure
        import matplotlib.ticker as ticker
        import matplotlib.gridspec as gridspec

        # Change fonts globally - for all figures/subsplots at once.
        #from matplotlib import rc
        #rc('font', **{'family': 'Times New Roman'})
        import matplotlib.pylab as pylab
        params = {
        #'legend.fontsize': '28',
         'axes.titlesize':'large',
         'axes.labelsize': 'large',
         'xtick.labelsize':'medium',
         'ytick.labelsize':'medium'}
        pylab.rcParams.update(params)
        
        # Prepare "generic figure template".
        # Create figure object.
        fig = Figure()

        # Create a specific grid for DWM .
        gs = gridspec.GridSpec(3, 7)

        # Memory
        ax_memory = fig.add_subplot(gs[:, 0])  # all rows, col 0
        ax_attention = fig.add_subplot(gs[:, 1:3])  # all rows, col 2-3
        ax_snapshot = fig.add_subplot(gs[:, 3:5])  # all rows, col 4-5

        ax_inputs = fig.add_subplot(gs[0, 5:])  # row 0, span 2 columns
        ax_targets = fig.add_subplot(gs[1, 5:])  # row 0, span 2 columns
        ax_predictions = fig.add_subplot(gs[2, 5:])  # row 0, span 2 columns

        # Set ticks - for bit axes only (for now).
        ax_inputs.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
        ax_inputs.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
        ax_targets.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
        ax_targets.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
        ax_predictions.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
        ax_predictions.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
        ax_memory.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
        ax_memory.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
        ax_snapshot.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
        ax_snapshot.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
        ax_attention.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
        ax_attention.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))

        # Set labels.
        ax_inputs.set_title('Inputs')
        ax_inputs.set_ylabel('Control/Data bits')
        ax_targets.set_title('Targets')
        ax_targets.set_ylabel('Data bits')
        ax_predictions.set_title('Predictions')
        ax_predictions.set_ylabel('Data bits')
        ax_predictions.set_xlabel('Item number/Iteration')

        ax_memory.set_title('Memory')
        ax_memory.set_ylabel('Memory Addresses')
        ax_memory.set_xlabel('Content bits')
        ax_attention.set_title('Head attention')
        ax_attention.set_xlabel('Iteration')
        ax_snapshot.set_title('Snapshot/Bookmark Attention')
        ax_snapshot.set_xlabel('Iteration')

        fig.set_tight_layout(True)
        #gs.tight_layout(fig)
        #plt.tight_layout()
        #fig.subplots_adjust(left = 0)
        return fig

    def plot(self, data_tuple, predictions, sample_number = 0):
        """ 
        Interactive visualization, with a slider enabling to move forth and back along the time axis (iteration in a given episode).
        
        :param data_tuple: Data tuple containing 
           - input [BATCH_SIZE x SEQUENCE_LENGTH x INPUT_DATA_SIZE] and 
           - target sequences  [BATCH_SIZE x SEQUENCE_LENGTH x OUTPUT_DATA_SIZE]
        :param predictions: Prediction sequence [BATCH_SIZE x SEQUENCE_LENGTH x OUTPUT_DATA_SIZE]
        :param sample_number: Number of sample in batch (DEFAULT: 0) 
        """
        # Check if we are supposed to visualize at all.
        if not self.app_state.visualize:
            return False

        # Initialize timePlot window - if required.
        if self.plotWindow == None:
            from misc.time_plot import TimePlot
            self.plotWindow = TimePlot()

        # import time
        # start_time = time.time()
        inputs_seq = data_tuple.inputs[0].cpu().detach().numpy()
        targets_seq = data_tuple.targets[0].cpu().detach().numpy()
        predictions_seq = predictions[0].cpu().detach().numpy()

        # temporary for data with additional channel
        if len(inputs_seq.shape) == 3:
            inputs_seq = inputs_seq[0, :, :]

        # Create figure template.
        fig = self.generate_figure_layout()
        # Get axes that artists will draw on.
        (ax_memory, ax_attention, ax_snapshot, ax_inputs, ax_targets, ax_predictions) = fig.axes
        
        # Set intial values of displayed  inputs, targets and predictions - simply zeros.
        inputs_displayed = np.transpose(np.zeros(inputs_seq.shape))
        targets_displayed = np.transpose(np.zeros(targets_seq.shape))
        predictions_displayed = np.transpose(np.zeros(predictions_seq.shape))

        head_attention_displayed = np.zeros((self.cell_state_history[0][1].shape[-1], targets_seq.shape[0]))
        snapshot_attention_displayed = np.zeros((self.cell_state_history[0][2].shape[-1], targets_seq.shape[0]))

        # Log sequence length - so the user can understand what is going on.
        logger = logging.getLogger('ModelBase')
        logger.info("Generating dynamic visualization of {} figures, please wait...".format(inputs_seq.shape[0]))
        
        # Create frames - a list of lists, where each row is a list of artists used to draw a given frame.
        frames = []
        
        for i, (input_element, target_element, prediction_element,  (memory, wt, wt_d)) in enumerate(
                zip(inputs_seq, targets_seq, predictions_seq,  self.cell_state_history)):
            # Display information every 10% of figures.
            if (inputs_seq.shape[0] > 10) and (i % (inputs_seq.shape[0] // 10) == 0):
                logger.info("Generating figure {}/{}".format(i, inputs_seq.shape[0]))

            # Update displayed values on adequate positions.
            inputs_displayed[:, i] = input_element
            targets_displayed[:, i] = target_element
            predictions_displayed[:, i] = prediction_element

            memory_displayed = memory[0]
            # Get attention of head 0.
            head_attention_displayed[:, i] = wt[0, 0, :]
            snapshot_attention_displayed[:, i] = wt_d[0, 0, :]

            # Create "Artists" drawing data on "ImageAxes".
            artists = [None] * len( fig.axes)
            
             # Tell artists what to do;)
            artists[0] = ax_memory.imshow(np.transpose(memory_displayed), interpolation='nearest', aspect='auto')
            artists[1] = ax_attention.imshow(head_attention_displayed, interpolation='nearest', aspect='auto')
            artists[2] = ax_snapshot.imshow(snapshot_attention_displayed, interpolation='nearest', aspect='auto')
            artists[3] = ax_inputs.imshow(inputs_displayed, interpolation='nearest', aspect='auto')
            artists[4] = ax_targets.imshow(targets_displayed, interpolation='nearest', aspect='auto')
            artists[5] = ax_predictions.imshow(predictions_displayed, interpolation='nearest', aspect='auto')

            # Add "frame".
            frames.append(artists)

        # print("--- %s seconds ---" % (time.time() - start_time))
        # Plot figure and list of frames.
        
        self.plotWindow.update(fig,  frames)
        return self.plotWindow.is_closed