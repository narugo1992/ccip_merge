import time

import numpy as np
import pandas as pd
from ditk import logging
from imgutils.metrics import ccip_batch_differences, ccip_default_threshold
from scipy.optimize import minimize
from tqdm import tqdm

from .index import get_np_feats
from .picked import PICKED_TAGS


def measure_tag_via_func(tag, func):
    logging.info(f'Reading embeddings for tag {tag!r} ...')
    embs = get_np_feats(tag)
    logging.info(f'Embedding shape: {embs.shape!r} ...')

    logging.info('Merging embeddings ...')
    start_time = time.time()
    result_emb = func(embs)
    duration = time.time() - start_time

    logging.info(f'Result embedding shape of {tag!r}: {result_emb.shape!r}.')
    distances = ccip_batch_differences([result_emb, *embs])[0, 1:]

    retval = {
        'mean_diff': distances.mean(),
        'same_ratio': (distances < ccip_default_threshold()).mean(),
        'time_cost': duration,
    }
    logging.info(f'Tag {tag!r}, mean diff: {retval["mean_diff"]:.4f}, '
                 f'same ratio: {retval["same_ratio"]:.4f}, time cost: {retval["time_cost"]:.4f}s.')
    return retval


def ccip_merge_func(embs):
    # TODO: just replace your function here!!!
    def objective_function(x):
        total_similarity = 0
        for vector in embs:
            total_similarity += np.dot(x, vector) / (np.linalg.norm(x) * np.linalg.norm(vector))
        return -total_similarity / embs.shape[0]

    initial_guess = np.random.rand(768)
    constraints = ({'type': 'eq', 'fun': lambda x: np.linalg.norm(x) - 1.0})
    result = minimize(
        objective_function, initial_guess,
        constraints=constraints,
    )

    mean_length = np.linalg.norm(embs, axis=1).mean()
    best_vec = result.x
    best_vec = best_vec * mean_length
    return best_vec


def get_metrics_of_tags(n: int = 100) -> pd.DataFrame:
    rows = []
    for tag in tqdm(PICKED_TAGS[:n]):
        logging.info(f'Merging for tag {tag!r} ...')
        metrics = measure_tag_via_func(tag, ccip_merge_func)
        rows.append({'tag': tag, **metrics})

    return pd.DataFrame(rows)


if __name__ == '__main__':
    logging.try_init_root(logging.INFO)
    df = get_metrics_of_tags(n=100)
    logging.info(str(df))
    logging.info(f'Mean diff: {df["mean_diff"].mean():.4f}, '
                 f'same ratio: {df["same_ratio"].mean():.4f}, '
                 f'time cost: {df["time_cost"].mean():.4f}s.')

    file = 'test_result.csv'
    logging.info(f'Saving result to {file!r} ...')
    df.to_csv(file, index=False)