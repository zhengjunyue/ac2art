# coding: utf-8

"""Set of functions to split a corpus ensuring triphones coverage"""

import os

import numpy as np

from data.utils import check_type_validity, CONSTANTS, import_from_string


def build_triphones_indexer(limit, corpus):
    """Build an index of triphones appearing in each utterance of a corpus.

    limit : minimum number of utterances a triphone must appear in
            to be indexed

    Return a dict associating the (reduced) set of triphones comprised
    in an utterance with the latter's name.
    """
    # Load the dependency functions associated with the corpus to index.
    load_phone_labels, get_utterances_list = import_from_string(
        module='data.%s.raw._loaders' % corpus,
        elements=['load_phone_labels', 'get_utterances_list']
    )
    # Define an auxiliary function to read an utterance's triphones.
    def load_triphones(name):
        """Load the set of triphones contained in a given utterance."""
        labels = load_phone_labels(name)
        return {
            '_'.join([phone[1] for phone in labels[i:i + 3]])
            for i in range(len(labels) - 2)
        }
    # Gather the sets of utterances' triphones and the full list of these.
    utterances = {
        name: load_triphones(name) for name in get_utterances_list()
    }
    all_triphones = {
        triphone for utt_triphones in utterances.values()
        for triphone in utt_triphones
    }
    # Select the triphones of interest.
    triphones = {
        triphone for triphone in all_triphones
        if sum(triphone in utt for utt in utterances.values()) >= limit
    }
    # Reduce the dict referencing triphones associated to each utterance.
    utterances_index = {
        utterance: [phone for phone in utt_triphones if phone in triphones]
        for utterance, utt_triphones in utterances.items()
    }
    return utterances_index


def build_initial_split(indexer):
    """Return a split of a corpus that ensures good triphones coverage.

    indexer : a dict associating sets of comprised triphones to
              utterances (as returned by `build_triphones_indexer`)

    Return a tuple of three lists of utterances, representing the
    train, validation and test filesets, ensuring that all triphones
    of interest (i.e. appearing in the provided indexer) are comprised
    at least once in each of the filesets.
    """
    filesets = [{'utt': [], 'phones': set()} for _ in range(3)]
    # Iterate over the list of utterances, in random order.
    for utterance in np.random.permutation(list(indexer.keys())):
        # Compute the number of covered triphones each fileset
        # would gain from incorporating the current utterance.
        gains = [
            sum(phone not in fileset['phones'] for phone in indexer[utterance])
            for fileset in filesets
        ]
        # Assign the utterance to the fileset that benefits the most of it.
        chosen = np.argmax(gains)
        filesets[chosen]['utt'].append(utterance)
        filesets[chosen]['phones'] = (
            filesets[chosen]['phones'].union(indexer[utterance])
        )
    # Check that all triphones appear in each fileset.
    all_covered = (
        filesets[0]['phones'] == filesets[1]['phones'] == filesets[2]['phones']
    )
    # If there are coverage issues, start over again.
    if not all_covered:
        print(
            'Error: invalid initial repartition. The algorithm was restarted.'
        )
        return build_initial_split(indexer)
    # Otherwise, return the designed filesets.
    return [fileset['utt'] for fileset in filesets]


def adjust_filesets(filesets, pct_train, indexer):
    """Transfer some utterances between filesets to adjust their sizes.

    filesets  : a tuple of three lists of utterances, representing the
                filesets (as returned by `build_initial_split`)
    pct_train : percentage of observations used as training data
                (float between 0 and 1) ; the rest will be divided
                equally between the validation and test sets
    indexer   : a dict associating sets of comprised triphones to
                utterances (as returned by `build_triphones_indexer`)

    Return a tuple of three lists of utterances, representing the
    train, validation and test filesets.

    The utterances moved from a fileset to another are selected
    randomly, under the condition that their removal does not
    deprive the initial fileset from a triphone of interest.
    """
    # Compute theoretical sizes of the filesets.
    total = sum(len(fileset) for fileset in filesets)
    n_obs = [0] * 3
    n_obs[0] = int(np.ceil(total * pct_train))
    n_obs[1] = int(np.floor((total - n_obs[0]) / 2))
    n_obs[2] = total - sum(n_obs)
    taken_out = []
    # Remove observations from filesets which are too large,
    # making sure that it does not alter triphones coverage.
    for fileset, size in zip(filesets, n_obs):
        if len(fileset) > size:
            n_moves = len(fileset) - size
            moved = []
            while len(moved) < n_moves:
                chosen = np.random.choice(fileset)
                movable = all(
                    sum(phone in indexer[utt] for utt in fileset) > 1
                    for phone in indexer[chosen]
                )
                if movable:
                    moved.append(chosen)
                    fileset.remove(chosen)
            taken_out.extend(moved)
    # Dispatch the selected observations in the filesets which are too small.
    for fileset, size, in zip(filesets, n_obs):
        for _ in range(size - len(fileset)):
            chosen = np.random.choice(taken_out)
            fileset.append(chosen)
            taken_out.remove(chosen)
    # Return the adjusted filesets.
    return filesets


def store_filesets(filesets, corpus):
    """Write lists of utterances defining sub-filesets of a corpus.

    filesets : dict associating a list of utterances' names to str
               keys serving as fileset names
    corpus  : name of the corpus which the filesets concern (str)
    """
    check_type_validity(filesets, dict, 'filesets')
    # Build the output 'filesets' folder if needed.
    base_folder = CONSTANTS['%s_processed_folder' % corpus]
    output_folder = os.path.join(base_folder, 'filesets')
    if not os.path.isdir(output_folder):
        os.makedirs(output_folder)
    # Iteratively write the filesets to their own txt file.
    for set_name, fileset in filesets.items():
        path = os.path.join(output_folder, set_name + '.txt')
        with open(path, 'w', encoding='utf-8') as file:
            file.write('\n'.join(fileset))


def split_corpus_prototype(pct_train, limit, seed, corpus, lowest_limit):
    """Split the {0} corpus, ensuring good triphones coverage of the sets.

    pct_train : percentage of observations used as training data; the
                rest will be divided equally between the validation
                and test sets float (between 0 and 1, default .7)
    limit     : minimum number of utterances a triphone must appear in
                so as to be taken into account (int, default {1})
    seed      : optional random seed to use

    Produce three lists of utterances, composing train, validation
    and test filesets. The filesets are built so that each triphone
    present in at list `limit` utterances appears at least once in
    each fileset. The filesets' length will also be made to match
    the `pct_train` argument.

    To achieve this, the split is conducted in two steps.
    * First, utterances are iteratively drawn in random order, and
    added to the fileset to which they add the most not-yet-covered
    triphones. This mechanically results in three filesets correctly
    covering the set of triphones (if not, the algorithm is restarted).
    * Then, utterances are randomly removed from the fileset(s) which
    prove too large compared to the desired split, under the condition
    that their removal does not break the triphones-coverage property.
    These utterances are then randomly re-assigned to the filesets
    which are too small.

    Note: due to the structure of the {0} utterances, using a `limit`
          parameter under {1} will generally fail.

    The produced filesets are stored to the filesets/ subfolder of the
    processed {0} folder, in txt files named 'train', 'validation'
    and 'test'.
    """
    # Check arguments' validity
    check_type_validity(pct_train, float, 'pct_train')
    check_type_validity(limit, int, 'limit')
    if not 0 < pct_train < 1:
        raise ValueError('Invalid `pct_train` value: %s.' % pct_train)
    if limit < 3:
        raise ValueError('Minimum `limit` value is 3.')
    elif limit < lowest_limit:
        print('Warning: using such a low `limit` value is due to fail.')
    # Build the filesets.
    np.random.seed(seed)
    indexer = build_triphones_indexer(limit, corpus)
    filesets = build_initial_split(indexer)
    filesets = adjust_filesets(filesets, pct_train, indexer)
    # Write the produced filesets to txt files.
    filesets_dict = dict(zip(('train', 'validation', 'test'), filesets))
    store_filesets(filesets_dict, corpus)


def build_split_corpus(corpus, lowest_limit):
    """Build a corpus-specific `split_corpus` function."""
    # Define the corpus-specific function.
    def split_corpus(pct_train=.7, limit=lowest_limit, seed=None):
        """Split the corpus."""
        return split_corpus_prototype(
            pct_train, limit, seed, corpus, lowest_limit
        )
    # Adjust the function's docstring and return it.
    split_corpus.__doc__ = (
        split_corpus_prototype.__doc__.format(corpus, lowest_limit)
    )
    return split_corpus
