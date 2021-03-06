import atexit, os, h5py, glob, logging, psutil
import numpy as np
from h5py import Dataset
import dask.array as da

logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__ + 'hdf5_filemanager')

SOURCE_FILES = list() # opened files to be closed after processing

@atexit.register
def clean_files():
    """ Clean the global list of opened files that are being used to create dask arrays. 
    """
    for f in SOURCE_FILES:
        f.close()


def file_in_list(file_pointer, file_list):
    """ Check if a file pointer points to the same file than another file pointer in the file_list.
    """
    for fp in file_list:
        if file_pointer == fp:
            return True 

    return False


class HDF5_manager:
    def __init__(self):
        self.filename_regex = "[0-9]*_[0-9]*_[0-9]*.hdf5"


    def remove_all(self, dirpath):
        workdir = os.getcwd()
        os.chdir(dirpath)
        for filename in glob.glob("*.hdf5"):
            os.remove(filename)
        os.chdir(workdir)
        

    def clean_directory(self, dirpath):
        """ Remove intermediary files from split/rechunk from a directory (matching chunks regex).
        See __init__ for regex
        """
        workdir = os.getcwd()
        os.chdir(dirpath)
        for filename in glob.glob(self.filename_regex):
            os.remove(filename)
        os.chdir(workdir)
    

    def get_input_files(self, input_dirpath):
        """ Return a list of input files paths matching chunks regex
        See __init__ for regex
        """
        workdir = os.getcwd()
        os.chdir(input_dirpath)
        infiles = list()
        for filename in glob.glob(self.filename_regex):
            infiles.append(os.path.join(input_dirpath, filename))
        os.chdir(workdir)
        return infiles


    def get_filepath(self, i, j, k, dirpath):
        filename = f'{i}_{j}_{k}.hdf5'
        return os.path.join(dirpath, filename)


    def read_data(self, i, j, k, dirpath, slices):
        """ Read part of a chunk
        """
        filename = f'{i}_{j}_{k}.hdf5'
        input_file = os.path.join(dirpath, filename)

        if slices == None:
            # print("read all")
            with h5py.File(input_file, 'r') as f:
                return f['/data'][:,:,:]

        s = slices
        # print("read part")
        with h5py.File(input_file, 'r') as f:
            data = np.empty((s[0][1]-s[0][0],s[1][1]-s[1][0],s[2][1]-s[2][0]), dtype=np.float16)
            f['/data'].read_direct(data, np.s_[s[0][0]:s[0][1],s[1][0]:s[1][1],s[2][0]:s[2][1]])
        return data


    def read_data_from_fp(self, filepath, slices):
        """ Read part of a chunk
        """
        if slices == None:
            with h5py.File(filepath, 'r') as f:
                return f['/data'][:,:,:]

        s = slices
        with h5py.File(filepath, 'r') as f:
            data = np.empty((s[0][1]-s[0][0],s[1][1]-s[1][0],s[2][1]-s[2][0]), dtype=np.float16)
            f['/data'].read_direct(data, np.s_[s[0][0]:s[0][1],s[1][0]:s[1][1],s[2][0]:s[2][1]])
        return data


    def get_dataset(self, filepath):
        with h5py.File(filepath, 'r') as f:
            return f['/data']


    def write_data(self, i, j, k, outdir_path, data, s2, O, dtype=np.float16):
        """ Write data at region _slices in outfilepath
        Used to create a file of shape O and write data into a part of that file
        """
        out_filename = f'{i}_{j}_{k}.hdf5'
        outfilepath = os.path.join(outdir_path, out_filename)

        if os.path.isfile(outfilepath):
            mode = 'r+'
        else:
            mode = 'w'

        empty_dataset = False
        with h5py.File(outfilepath, mode) as f:
            if not "/data" in f.keys():
                if O != data.shape:
                    outdset = f.create_dataset("/data", O, data=np.empty(O, dtype=dtype), dtype=dtype)  # initialize an empty dataset
                    outdset[s2[0][0]:s2[0][1],s2[1][0]:s2[1][1],s2[2][0]:s2[2][1]] = data
                else:
                    f.create_dataset("/data", O, data=data, dtype=dtype)
                empty_dataset = True
            else:
                f["/data"][s2[0][0]:s2[0][1],s2[1][0]:s2[1][1],s2[2][0]:s2[2][1]] = data

        return empty_dataset


    def write(self, outfilepath, data, cs, _slices=None, dtype=np.float16): 
        """ Write data in file, data.shape == file.shape
        Used to write original array or complete file
        """
        if os.path.isfile(outfilepath):
            mode = 'r+'
        else:
            mode = 'w'

        with h5py.File(outfilepath, mode) as f:

            if _slices != None:
                if not "/data" in f.keys():
                    null_arr = np.empty(cs, dtype=dtype)
                    outdset = f.create_dataset("/data", cs, data=null_arr, dtype=dtype) 
                else:
                    outdset = f["/data"]

                outdset[_slices[0][0]:_slices[0][1],_slices[1][0]:_slices[1][1],_slices[2][0]:_slices[2][1]] = data
            else:
                f.create_dataset("/data", cs, data=data, dtype=dtype)            


    def test_write(self, outfile_path, s, subarr_data):
        """ Used in baseline for verifying subarray writing
        """
        with h5py.File(outfile_path, 'r') as f:
            stored = f['/data'][s[0][0]:s[0][1],s[1][0]:s[1][1],s[2][0]:s[2][1]]
            if np.allclose(stored, subarr_data):
                logger.debug("[success] data successfully stored.")
            else:
                logger.debug("[error] in data storage")


    def close_infiles(self):
        clean_files()


    def read_all(self, filepath):
        """ Read all the file and return the whole array
        """
        dset = self.get_dataset(filepath, '/data')
        return dset[()]


    def inspect_h5py_file(self, f):
        """ Get information about an HDF5 file
        """
        print(f'Inspecting h5py file...')
        for k, v in f.items():
            print(f'\tFound object {v.name} at key {k}')
            if isinstance(v, Dataset):
                print(f'\t - Object type: dataset')
                print(f'\t - Physical chunks shape: {v.chunks}')
                print(f'\t - Compression: {v.compression}')
                print(f'\t - Shape: {v.shape}')
                print(f'\t - Size: {v.size}')
                print(f'\t - Dtype: {v.dtype}')
            else:
                print(f'\t - Object type: group')
        pass


    def get_dataset(self, file_path, dataset_key):
        """ Get dataset from hdf5 file 
        """

        def check_extension(file_path, ext):
            if file_path.split('.')[-1] != ext:
                return False 
            return True

        if not os.path.isfile(file_path):
            print("looking for ", file_path)
            raise FileNotFoundError()

        if not check_extension(file_path, 'hdf5'):
            raise ValueError("This is not a hdf5 file.") 

        f = h5py.File(file_path, 'r')

        if not f.keys():
            raise ValueError('No dataset found in the input file. Aborting.')

        if not file_in_list(f, SOURCE_FILES):
            SOURCE_FILES.append(f)

        # print("Loading file...")
        self.inspect_h5py_file(f)

        return f[dataset_key]


    def check_split_merge(self, filepath1, filepath2):
        f = h5py.File(filepath1)
        f2 = h5py.File(filepath2)

        arr1 = da.from_array(f['/data'])
        arr2 = da.from_array(f2['/data'])

        return da.all_close(arr1, arr2)