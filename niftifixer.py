from os import walk
import nibabel as nib
import numpy as np
import pathlib
import argparse
from itertools import chain

def locate_t1ws(path):
    t1ws = []
    for root, dirs, files in walk(path):
        for file in files:
            if file.endswith('.nii.gz') or file.endswith('nii'):
                if 't1' in file.lower() or '3d' in file.lower() or 'anat' in file.lower():
                    t1ws.append(root + '/' + file)
    return t1ws

class GetNiftiInfo():
    def __init__(self, nifti_path):
        self.nifti_path = nifti_path
        self.nifti = nib.load(nifti_path)
        self.shape = self.nifti.shape
        self.zooms = self.nifti.header.get_zooms()
        self.is_single_volume = self.check_if_single_volume()
        self.is_3D = self.check_dims_for_anat()
    
    def show_info(self):
        print(f'Nifti path: {self.nifti_path}')
        print(f'Shape: {self.shape}')
    
    def check_dims_for_anat(self):
        # check to see that the nifti is a 3D volume
        if len(self.shape) == 3:
            self.is_3D = True
            return True
        elif len(self.shape) == 4:
            self.is_3D = False
            if self.shape[3] == 1:
                self.is_single_volume = True
            else:
                self.is_single_volume = False
            return False
        else:
            self.is_3D = False
            return False
    
    def check_if_single_volume(self):
        if len(self.shape) == 3:
            return True
        else:
            return False
        
    def make_t1w_3D(self, first_run_only=False, delete_original=False, rename_original=False):
        if self.is_single_volume:
            return self.nifti
        else:
            # get the number of frames
            num_frames = self.shape[3]
            
            # first check to see if the frames are identical in contents/pixel values
            # if they are we choose one of them and save it as a 3D volume skipping the rest
            frames_to_compare = {}
            are_equal = []
            frame_num = 0
            while frame_num < num_frames:
                current_frame = self.nifti.get_fdata()[:,:,:,frame_num]
                other_frames = [f for f in range(self.shape[3])]
                other_frames.remove(frame_num)
                for next_frame_num in other_frames:
                    next_frame = self.nifti.get_fdata()[:,:,:,next_frame_num]
                    if np.array_equal(current_frame, next_frame):
                        are_equal.append((frame_num, next_frame_num))
                frame_num += 1

            print(f'Found {len(are_equal)} identical frames')
            if len(are_equal) > 0:
                print(f'Frames that are identical: {are_equal}')

            # check to see if all frames are identical
            if len(are_equal) == 0:
                # if all frames are identical set first_run_only to True
                use_these_frames = [f for f in range(self.shape[3])]
            elif 0 < len(are_equal) < (self.shape[3]):
                # pop any frames that are equal and only write out the ones that are not as individual runs
                remove_these = list(set(list(chain.from_iterable(are_equal))))
                print(f'Frames to remove: {remove_these}')
                # we want to keep one of these frames
                if set(remove_these) == set(range(self.shape[3])):
                    use_these_runs = [0]
                # remove any duplicates
                else:
                    use_these_runs = [f for f in range(len(self.shape[3])) if f not in remove_these]
            else:
                # if all frames are identical set first_run_only to True
                use_these_runs = [0]

            if first_run_only:
                use_these_runs = [0]

            for frame in use_these_runs:
                # create a new file name for each frame labeling it with the frame number as run number
                # instead of the original file name, if _T1w is present in the filename then place 
                # run- in front of _T1w, otherwise place run- in front of the .nii
                if len(use_these_runs) > 1:
                    if '_T1w' in pathlib.Path(self.nifti_path).name:
                        out_name = self.nifti_path.replace('_T1w', f'_run-0{frame + 1}_T1w')
                    else:
                        out_name = self.nifti_path.replace('.nii', f'_run-0{frame + 1}.nii')
                else:
                    out_name = self.nifti_path

                new_run = nib.Nifti1Image(self.nifti.get_fdata()[:,:,:,frame], affine=self.nifti.affine, header=self.nifti.header)

                nib.save(new_run, out_name)
            
            if delete_original and len(are_equal) > 0:
                pathlib.Path(self.nifti_path).unlink()
            
            if rename_original:
                nib.save(self.nifti, "original_" + pathlib.Path(self.nifti_path).name)
            
            return None

if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Fix nifti files')
    parser.add_argument('path', type=str, help='Path to nifti files')
    parser.add_argument('--first_run_only', action='store_true', default=False, help='Only use the first run')
    parser.add_argument('--delete_original', action='store_true', default=False, help='Delete the original file')
    args = parser.parse_args()

    nifti_path = pathlib.Path(args.path)
    if nifti_path.is_dir():
        t1ws = locate_t1ws(nifti_path)
        print(f'Found {len(t1ws)} T1w files at {args.path}:')
        for t1w in t1ws:
            print(t1w)
        bad_t1ws = []
        for t1w in t1ws:
            nii_info = GetNiftiInfo(t1w)
            if not nii_info.is_3D:
                bad_t1ws.append(t1w)
        print(f'Found {len(bad_t1ws)} bad T1w files')
        for bad_t1w in bad_t1ws:
            print(bad_t1w)
        raw_input = input('Would you like to fix these files? [y/n]: ')
        if 'y' in str(raw_input).lower():
            if args.delete_original or args.first_run_only:
                print("You've selected an option that will delete the original file, this cannot be undone")
                for bad_t1w in bad_t1ws:
                    print(f"The following original files will be deleted {bad_t1w}")
                input("Enter 'y' to continue: ")
                if 'y' not in str(raw_input).lower():
                    exit(1)
            for bad_t1w in bad_t1ws:
                nii_info = GetNiftiInfo(bad_t1w)
                nii_info.make_t1w_3D(args.first_run_only, delete_original=args.delete_original)
    elif nifti_path.is_file():
        nii_info = GetNiftiInfo(nifti_path)
        if not nii_info.is_3D:
            print(f'The file {nifti_path} is not a 3D volume')
            raw_input = input('Would you like to fix this file? [y/n]: ')
            if 'y' in str(raw_input).lower():
                nii_info.make_t1w_3D(args.average_runs, args.first_run_only, delete_original=args.delete_original)
    else:
        print(f'The path {nifti_path} is not a file or directory')
        exit(1)
