# coding: utf-8
#
# Copyright 2018 Paul Andrey
#
# This file is part of ac2art.
#
# ac2art is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ac2art is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ac2art.  If not, see <http://www.gnu.org/licenses/>.

"""Submodule defining corpus-specific data processing pipelines.


As of now, the supported corpora include the following:
  mngu0 : mngu0 day-one acoustic and ema data
  mocha : mocha-timit data for the two initial speakers
  mspka : mspka first session data


For each supported corpus, a `ac2art.corpora.<corpus>` submodule
is defined, which should be explicitely imported by the user (to
avoid useless overhead, these submodules are not processed upon
importing ac2art).


Note that using a corpus requires to actually dispose of the data,
and to have referred their location, as well as that the folder in
which pre-processed data is to be written, in the config.json file
at the root of the package.


Each corpus's submodule consists in multiple units of code, which
respect the following mandatory structure of implemented functions,
may add some internal dependency functions, and heavily rely on the
use of functions contstructor implemented in the `prototype` submodule:


`ac2art.corpora.<corpus>.abkhazia`
    copy_wavs
    get_transcription
    (the last one may wrap `prototype.utils.read_transcript`)

`ac2art.corpora.<corpus>.raw`
    get_utterances_list
    load_wav
    load_phone_labels
    load_ema
    load_voicing
    (the latter two are built using `prototype.raw.build_ema_loaders`)

`ac2art.corpora.<corpus>.preprocess`
    extract_utterances_data
    compute_moments
    normalize_files
    split_corpus
    (all built using `prototype.preprocess` functions)

`ac2art.corpora.<corpus>.load`
    change_loading_setup
    get_loading_setup
    get_norm_parameters
    get_utterances
    load_acoustic
    load_ema
    load_utterance
    load_dataset
    (all built using `prototype.load.build_loading_functions`)

`ac2art.corpora.<corpus>.abx`
    extract_h5_features
    (built with `prototype.abx.build_h5features_extractor`)
    abx_from_features
    make_abx_task
    make_itemfile
    load_abx_scores
    (all built with `prototype.abx.build_abxpy_callers`)


To add support for a corpus, one should thus implement the necessary
functions in the `raw` and `abkhazia` subunits, then use the prototype
wrappers to build the rest of the subunits and functions, following
what is done for the already supported corpora.


Note that for the mocha and mspka corpora, adding support to
data from additional recording sessions / speakers should be
straight-forward, requiring only to edit the list of speakers
in `ac2art.corpora.<corpus>.raw._loaders.py` (SPEAKERS) constant.


Also note that for these same two corpora, enhanced versions of
the phone labels files must be use so as to compute MFCC features
using abkhazia. They must thus be downloaded and placed in the
folder of processed data, under the 'labels' subfolder.
"""


from . import prototype
