def get_dims_to_keep(volumestokeep):
    if 4 in volumestokeep:
        return [0,1,2]
    elif 3 in volumestokeep:
        return [0,1]
    elif 1 in volumestokeep:
        return [0]
    else
        return list()


def get_grads(R, O, B, dims_to_keep):
    """ Grads corresponds to all the out borders of both output files and buffers.
    """
    grads_o = [set(range(O[i], R[i], O[i])) for i in range(3)]
    grads_b = [set(range(B[i], R[i], B[i])) for i in range(3)]
    grads = [set().union(grads_o[i], grads_b[i]) for i in range(3)]
    for i in range(3):
        if i in dims_to_keep:
            for buff_border in grads_b[i]:
                if not buff_border in grads_o[i]:
                    grads[i].remove(buff_border)
    return grads


def get_volumes(grads):
    d = dict()
    prev_i, prev_j, prev_k = (0,0,0)

    for i in range(1, len(grads[0])):
        for j in range(1, len(grads[1])):
            for k in range(1, len(grads[2])):
                add_to_dict(d, Volume((prev_i, prev_j, prev_k), (grads[0][i], grads[1][j], grads[2][k])))
                prev_k = grads[2][k]
            prev_j = grads[1][j]
        prev_i = grads[0][i]

    return d


def add_to_dict(d, grads_o, volume, _3d_to_numeric_pos_dict):
    """
        volume: volume to add to the dictionary 
    """
    outfile_pos = list()
    for dim in range(3):
        for i, upper_border in enumerate(grads_o):
            if upper_border >= volume.p2[dim] and lower_border <= volume.p1[dim]:
                outfile_pos.append(i)

    outfile_pos = _3d_to_numeric_pos_dict[outfile_pos]
    if not outfile_pos in d:
        d[outfile_pos] = list()
    d[outfile_pos].append(volume)


def compute_zones(B, O, R, volumestokeep) #, buffers_partition, outfiles_partititon, buffers_volumes, outfiles_volumes):
    """ Main function of the module. Compute the "arrays" and "regions" dictionary for the resplit case.

    Arguments:
    ----------
        B: buffer shape
        O: output file shape
        R: shape of reconstructed image
        volumestokeep: volumes to be kept by keep strategy
    """
    return get_volumes(get_grads(R, O, B, get_dims_to_keep(volumestokeep)))
    # return arrays_dict, buffer_to_outfiles, nb_file_openings, nb_inside_seeks