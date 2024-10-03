from os import walk
import nibabel as nib
import numpy as np
import pathlib
import argparse

def locate_t1ws(path):
    t1ws = []
    for root, dirs, files in walk(path):
        for file in files:
            if file.endswith('_T1w.nii.gz') or file.endswith('_T1w.nii'):
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
            if first_run_only:
                num_frames = 1
            # combine all frames into a single 3D volume
            for frame in range(num_frames):
                # create a new file name for each frame labeling it with the frame number as run number
                # instead of the original file name, if _T1w is present in the filename then place 
                # run- in front of _T1w, otherwise place run- in front of the .nii 
                if '_T1w' in pathlib.Path(self.nifti_path).name:
                    out_name = self.nifti_path.replace('_T1w', f'_run-0{frame + 1}_T1w')
                else:
                    out_name = self.nifti_path.replace('.nii', f'_run-0{frame + 1}.nii')

                new_run = nib.Nifti1Image(self.nifti.get_fdata()[:,:,:,frame], affine=self.nifti.affine, header=self.nifti.header)
                
                # no reason to save run numbers if there's only one run
                if first_run_only:
                    out_name = self.nifti_path.replace("_run-01", "")
                nib.save(new_run, out_name)
            
            if delete_original or first_run_only:
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
