# coding: utf-8

"""Class implementing auto-encoder networks in tensorflow."""

import tensorflow as tf

from neural_networks.components import build_rmse_readouts
from neural_networks.models import MultilayerPerceptron
from neural_networks.utils import check_type_validity, onetimemethod


class AutoEncoder(MultilayerPerceptron):
    """Docstring."""

    def __init__(
            self, input_shape, n_targets, encoder_config, decoder_config,
            optimizer=None
        ):
        """Instantiate the auto-encoder network.

        input_shape    : shape of the input data fed to the network,
                         with the number of samples as first component
        n_targets      : number of real-valued targets to predict
        encoder_config : list of tuples specifying the encoder's architecture
        decoder_config : list of tuples specifying the decoder's architecture
        optimizer      : tensorflow.train.Optimizer instance (by default,
                         Adam optimizer with 1e-3 learning rate)

        The `encoder_config` and `decoder_config` arguments should
        be of a similar form as the `layers_config` argument of any
        `DeepNeuralNetwork` instance, i.e. lists of tuples specifying
        a layer configuration each, made of a layer class (or short name),
        a number of units (or a cutoff frequency for filters) and an
        optional dict of keyword arguments.

        Readout layer are automatically added between the encoder and
        decoder parts, and on top of the latter. They are fully-connected
        layers with identity activation.
        """
        # Check some arguments' validity.
        check_type_validity(encoder_config, list, 'encoder_config')
        check_type_validity(decoder_config, list, 'decoder_config')
        check_type_validity(input_shape, (list, tuple), 'input_shape')
        # Define a function specifying readout layers.
        def get_readout(part, n_units):
            """Return the configuration of a network part's readout layer."""
            kwargs = {'activation': 'identity', 'name': part + '_readout'}
            return [('dense_layer', n_units, kwargs)]
        # Aggregate the encoder's and decoder's layers.
        layers_config = (
            encoder_config + get_readout('encoder', n_targets)
            + decoder_config + get_readout('decoder', input_shape[1])
        )
        # Initialize the auto-encoder network.
        super().__init__(
            input_shape, n_targets, layers_config, optimizer=optimizer
        )
        # Record initialization arguments.
        self._init_arguments['encoder_config'] = encoder_config
        self._init_arguments['decoder_config'] = decoder_config
        # Remove inherited arguments which are of no use.
        self._init_arguments.pop('norm_params')
        self._init_arguments.pop('top_filter')

    def _adjust_init_arguments_for_saving(self):
        """Adjust `_init_arguments` attribute before dumping the model.

        Return a tuple of two dict. The first is a copy of the keyword
        arguments used at initialization, containing only values which
        numpy.save can serialize. The second associates to non-serializable
        arguments' names a dict enabling their (recursive) reconstruction
        using the `neural_networks.utils.instantiate` function.
        """
        init_args, rebuild_init = super()._adjust_init_arguments_for_saving()
        init_args.pop('layers_config')
        return init_args, rebuild_init

    @onetimemethod
    def _build_readout_layer(self):
        """Empty method, solely included to respect the API standards."""
        pass

    @onetimemethod
    def _build_readouts(self):
        """Build wrappers of the network's predictions and errors."""
        def build_readouts(part, true_data):
            """Build the error readouts of a part of the network."""
            readouts = build_rmse_readouts(
                self.layers[part + '_readout'].output, true_data
            )
            for name, readout in readouts.items():
                self.readouts[part + '_' + name] = readout
        # Use the previous function to build partial RMSE readouts.
        build_readouts('encoder', self.holders['targets'])
        build_readouts('decoder', self.holders['input'])
        #
        self.readouts['rmse'] = tf.concat([
            self.readouts['encoder_rmse'], self.readouts['decoder_rmse']
        ], axis=0)

    def score(self, input_data, targets):
        """Compute the root mean square prediction errors of the network.

        input_data : input data to be rebuilt by the network's decoder part
        targets    : target data to be rebuilt by the network's encoder part

        Return a couple of numpy arrays containing respectively
        the prediction and reconstruction by-channel root mean
        square errors.
        """
        feed_dict = self.get_feed_dict(input_data, targets)
        scores = [self.readouts['encoder_rmse'], self.readouts['decoder_rmse']]
        return self.session.run(scores, feed_dict)