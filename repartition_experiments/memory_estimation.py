import argparse, logging, json, sys


def get_arguments():
    """ Get arguments from console command.
    """
    parser = argparse.ArgumentParser(description="")
    
    parser.add_argument('paths_config', 
        action='store', 
        type=str, 
        help='Path to configuration file containing paths of data directories.')

    return parser.parse_args()


def load_json(filepath):
    with open(filepath) as f:
        return json.load(f)


if __name__ == "__main__":

    args = get_arguments()
    paths = load_json(args.paths_config)
    
    for k, v in paths.items():
        if "PYTHONPATH" in k:
            sys.path.insert(0, v)
            
    from repartition_experiments.algorithms.keep_algorithm import get_input_aggregate
    from repartition_experiments.algorithms.utils import get_volumes, numeric_to_3d_pos, get_theta
    from repartition_experiments.baseline_seek_model import get_cuts, preprocess
    from repartition_experiments.algorithms.utils import get_named_volumes, get_blocks_shape, numeric_to_3d_pos, get_theta
    from repartition_experiments.algorithms.keep_algorithm import get_input_aggregate

    import logging
    import logging.config
    logging.config.dictConfig({
        'version': 1,
        'disable_existing_loggers': True,
    })

    R = (1,120,120)
    B = (1,60,60)
    O = (1,40,40)
    nb_bytes_per_voxel = 2

    buffers_partition = get_blocks_shape(R, B)
    buffers_volumes = get_named_volumes(buffers_partition, B)

    k_remainder_list = [0]
    j_remainder_list = [0] * buffers_partition[2]
    i_remainder_list = [0] * (buffers_partition[2] * buffers_partition[1])
    print(f"Lists initialization...")
    print(f"k: {k_remainder_list}")
    print(f"j: {j_remainder_list}")
    print(f"i: {i_remainder_list}")

    nb_voxels_max = 0 
    nb_voxels = B[0] * B[1] * B[2]
    print(f"Initialization nb voxels (=1 buffer): {nb_voxels}")
    i, j, k = 0, 1, 2
    for buffer_index in buffers_volumes.keys():
        print(f"Processing buffer {buffer_index}")
        _3d_index = numeric_to_3d_pos(buffer_index, buffers_partition, order='C')
        theta, omega = get_theta(buffers_volumes, buffer_index, _3d_index, O, B)
        print(f"3d buffer index: {_3d_index}")

        F1 = omega[k] * theta[j] * theta[i]
        F2 = theta[k] * omega[j] * theta[i]
        F3 = omega[k] * omega[j] * theta[i]
        F4 = theta[k] * theta[j] * omega[i]
        F5 = omega[k] * theta[j] * omega[i]
        F6 = theta[k] * omega[1] * omega[i]
        F7 = omega[k] * omega[j] * omega[i]

        if theta[i] >= O[i] and theta[j] >= O[j] and omega[k]  >= O[k]:
            F1 = 0
        if theta[i] >= O[i] and omega[j] >= O[j] and theta[k]  >= O[k]:
            F2 = 0
        if theta[i] >= O[i] and omega[j] >= O[j] and omega[k]  >= O[k]:
            F3 = 0
        if omega[i] >= O[i] and theta[j] >= O[j] and theta[k]  >= O[k]:
            F4 = 0
        if omega[i] >= O[i] and theta[j] >= O[j] and omega[k]  >= O[k]:
            F5 = 0
        if omega[i] >= O[i] and omega[j] >= O[j] and theta[k]  >= O[k]:
            F6 = 0
        if omega[i] >= O[i] and omega[j] >= O[j] and omega[k]  >= O[k]:
            F7 = 0

        k_remainder = F1
        j_remainder = F2 + F3
        i_remainder = F4 + F5 + F6 + F7

        index_j = _3d_index[2]
        index_i = _3d_index[1]*len(j_remainder_list) + _3d_index[0]

        nb_voxels -= k_remainder_list[0] + j_remainder_list[index_j] + i_remainder_list[index_i]

        k_remainder_list[0] = k_remainder
        j_remainder_list[index_j] = j_remainder
        i_remainder_list[index_i] = i_remainder

        nb_voxels += k_remainder_list[0] + j_remainder_list[_3d_index[1]] + i_remainder_list[_3d_index[1]*len(j_remainder_list) + _3d_index[0]]

        print(f"k: {k_remainder_list}")
        print(f"j: {j_remainder_list}")
        print(f"i: {i_remainder_list}")
        print(f"Number of voxels: {nb_voxels}")

        if nb_voxels > nb_voxels_max:
            nb_voxels_max = nb_voxels

    print(f"Number of voxels max: {nb_voxels_max}")
    print(f"RAM consumed: {nb_voxels_max * nb_bytes_per_voxel}")