#!/usr/bin/env python

import h5py
import argparse
import re
import sys
from collections.abc import Sized

try:
    from colorama import Fore, Style, init
    init(autoreset=True)
    ERROR_COLOR = Fore.RED
    WARNING_COLOR = Fore.YELLOW
    PATH_COLOR = Fore.CYAN
    PASS_COLOR = Fore.GREEN
    RESET_COLOR = Style.RESET_ALL
except ImportError:
    # Fallback if colorama is not installed
    ERROR_COLOR = WARNING_COLOR = PATH_COLOR = PASS_COLOR = RESET_COLOR = ""

class CXIValidator:
    """
    Validates a CXI file against the Coherent X-ray Imaging file format
    specification (Version 1.6).
    """

    def __init__(self, filepath):
        self.filepath = filepath
        self.errors = []
        self.warnings = []
        self.h5file = None
        self.cxi_version = 0
        # From Sec A.8, data_type for Image class
        self.allowed_image_types = [
            "intensity", "electron density", "amplitude",
            "unphased amplitude", "autocorrelation"
        ]
        # From Sec A.8, data_space for Image class
        self.allowed_image_spaces = ["real", "diffraction"]
        # Implicit axes that don't need a dimension scale dataset
        self.implicit_axes = ['y', 'x', 'coordinate', 'dimension', 'dot_product', 'unit_cell']


    def add_error(self, message, path=""):
        self.errors.append(
            f"{ERROR_COLOR}ERROR  "
            f"{PATH_COLOR}[{path or self.h5file.name}]{RESET_COLOR}: "
            f"{message}"
        )

    def add_warning(self, message, path=""):
        self.warnings.append(
            f"{WARNING_COLOR}WARNING"
            f"{PATH_COLOR}[{path or self.h5file.name}]{RESET_COLOR}: "
            f"{message}"
        )

    def _check_exists(self, group, name, h5_type, required=True):
        """Helper to check for the existence and type of an HDF5 object."""
        if name not in group:
            if required:
                self.add_error(f"Required item '{name}' not found.", group.name)
            return None
        item = group[name]
        if not isinstance(item, h5_type):
            self.add_error(
                f"Item '{name}' has wrong type. "
                f"Expected {h5_type.__name__}, found {type(item).__name__}.",
                group.name
            )
            return None
        return item

    def _check_complex(self, dset):
        """Checks for CXI-compliant complex number format (Sec 5.1)."""
        dt = dset.id.get_type()
        if dt.get_nmembers() != 2:
            self.add_error(
                f"Complex dataset '{dset.name}' does not have exactly 2 members.",
                dset.parent.name
            )
            return
        if dt.get_member_name(0) != b'r' or dt.get_member_name(1) != b'i':
            self.add_error(
                f"Complex dataset '{dset.name}' has incorrect member names. "
                f"Expected ('r', 'i'), found ({dt.get_member_name(0)}, {dt.get_member_name(1)}).",
                dset.parent.name
            )

    def validate(self):
        """Main validation routine."""
        print(f"--- Starting validation for: {self.filepath} ---")
        try:
            with h5py.File(self.filepath, 'r') as self.h5file:
                self._validate_root()
        except Exception as e:
            self.add_error(f"Could not open or process HDF5 file: {e}")

        # --- Print Summary ---
        if self.warnings:
            print("\n--- Warnings ---")
            for w in self.warnings:
                print(w)
        
        if self.errors:
            print("\n--- Errors ---")
            for e in self.errors:
                print(e)

        print("\n--- Summary ---")
        if not self.errors:
            print(f"{PASS_COLOR}Validation successful.")
            if self.warnings:
                print(f"Found {len(self.warnings)} warning(s).")
            else:
                print("No errors or warnings found.")
        else:
            print(
                f"{ERROR_COLOR}Validation failed with {len(self.errors)} error(s) "
                f"and {len(self.warnings)} warning(s)."
            )
        return len(self.errors) == 0

    def _validate_sequential(self, keys, expected_prefix, path="/"):
        """
        Validates that keys are sequentially numbered with the expected prefix.
        For example, 'entry_1', 'entry_2', ..., 'entry_N'.
        path is the location in the HDF5 file where these keys are found
        """
        if not keys:
            return False
        keys.sort(key=lambda x: int(x.split('_')[-1]))  # Sort by number        
        for i, key in enumerate(keys):
            expected_key = f"{expected_prefix}_{i + 1}"
            if key != expected_key:
                self.add_error(
                    f"Must start from {expected_prefix}_1 and increment sequentially. Expected '{expected_key}', found '{key}'.",
                    f"{path}{key}"
                )
                return False
        return True

    def _validate_root(self):
        """Validates the root group of the CXI file (Sec A.1)."""
        # Check for cxi_version
        version_dset = self._check_exists(self.h5file, 'cxi_version', h5py.Dataset)
        if version_dset:
            if version_dset.dtype.kind not in 'iu': # Must be integer
                self.add_error("'cxi_version' must be an integer.", "/")
            else:
                self.cxi_version = version_dset[()]
        
        
        # Find and validate all entry groups
        entry_keys = [k for k in self.h5file.keys() if re.fullmatch(r'entry_\d+', k)]
        if not entry_keys:
            self.add_error("No 'entry_N' groups found in the file root.", "/")
            return
        self._validate_sequential(entry_keys, "entry", path="/")              

        # Check optional number_of_entries
        num_entries_dset = self._check_exists(self.h5file, 'number_of_entries', h5py.Dataset, required=False)
        if num_entries_dset and len(entry_keys) != num_entries_dset[()]:
            self.add_warning(
                f"'number_of_entries' ({num_entries_dset[()]}) does not match "
                f"the number of found 'entry_N' groups ({len(entry_keys)}).", "/"
            )
        
        for key in sorted(entry_keys):
            self._validate_entry(self.h5file[key])

    def _validate_entry(self, entry_group):
        """Validates an 'entry_N' group (Sec A.6)."""
        path = entry_group.name
        
        # Check for mandatory data_N group (Sec A.4)
        data_keys = [k for k in entry_group.keys() if re.fullmatch(r'data_\d+', k)]
        if not data_keys:
            self.add_error("Each entry must contain at least one 'data_N' group.", path)
        
        self._validate_sequential(data_keys, "data", path=path+"/") 

        # Validate all recognized CXI classes within the entry
        for classes in ['instrument', 'sample', 'image']:
            keys = [k for k in entry_group.keys() if re.fullmatch(rf'{classes}_\d+', k)]
            if keys:
                self._validate_sequential(keys, classes, path=path+"/")

        for key in entry_group:
            if re.fullmatch(r'data_\d+', key):
                self._validate_data(entry_group[key])
            elif re.fullmatch(r'instrument_\d+', key):
                self._validate_instrument(entry_group[key])
            elif re.fullmatch(r'image_\d+', key):
                self._validate_image(entry_group[key])
            elif re.fullmatch(r'sample_\d+', key):
                self._validate_sample(entry_group[key])
            # Add other class validators here (e.g., process, result)

    def _validate_data(self, data_group):
        """Validates a 'data_N' group (Sec A.4)."""
        path = data_group.name
        data_dset = self._check_exists(data_group, 'data', h5py.Dataset)
        if not data_dset: return
        
        self._validate_axes(data_dset)
        if data_dset.dtype.kind == 'c':
            self._check_complex(data_dset)

        errors_dset = self._check_exists(data_group, 'errors', h5py.Dataset, required=False)
        if errors_dset and errors_dset.shape != data_dset.shape:
            self.add_error("'errors' dataset shape must match 'data' dataset shape.", path)

    def _validate_instrument(self, inst_group):
        """Validates an 'instrument_N' group (Sec A.9)."""
        # Validate all recognized CXI classes within the instrument
        for classes in ['detector']:
            keys = [k for k in inst_group.keys() if re.fullmatch(rf'{classes}_\d+', k)]
            if keys:
                self._validate_sequential(keys, classes, path=inst_group.name+"/")

        for key in inst_group:
            if re.fullmatch(r'detector_\d+', key):
                self._validate_detector(inst_group[key])
            # Add validators for source, attenuator, etc. here

    def _validate_detector(self, det_group):
        """Validates a 'detector_N' group (Sec A.5)."""
        path = det_group.name
        data_dset = self._check_exists(det_group, 'data', h5py.Dataset)
        if not data_dset: return

        # Check for modular detector structure (Sec 9.3)
        module_id_dset = self._check_exists(det_group, 'module_identifier', h5py.Dataset, required=False)
        if module_id_dset:
            self._validate_axes(data_dset, is_modular=True)
            # For modular detectors, related fields should have a leading dimension
            # equal to the number of modules.
            num_modules = len(module_id_dset)
            for field in ['corner_position', 'basis_vectors']:
                field_dset = self._check_exists(det_group, field, h5py.Dataset, required=False)
                if field_dset and field_dset.shape[0] != num_modules:
                    self.add_error(f"Modular field '{field}' first dimension ({field_dset.shape[0]}) "
                                   f"should match number of modules ({num_modules}).", path)
        else:
            self._validate_axes(data_dset, is_modular=False)

    def _validate_image(self, image_group):
        """Validates an 'image_N' group (Sec A.8)."""
        path = image_group.name
        self._check_exists(image_group, 'data', h5py.Dataset)

        # Check data_space
        space_dset = self._check_exists(image_group, 'data_space', h5py.Dataset, required=False)
        if space_dset:
            try:
                space_val = space_dset[()].decode('utf-8')
                if space_val not in self.allowed_image_spaces:
                    self.add_error(f"'data_space' has invalid value '{space_val}'. "
                                   f"Allowed: {self.allowed_image_spaces}", path)
            except (AttributeError, TypeError):
                self.add_error("'data_space' must be a string.", path)

        # Check data_type
        type_dset = self._check_exists(image_group, 'data_type', h5py.Dataset)
        if type_dset:
            try:
                type_val = type_dset[()].decode('utf-8')
                if type_val not in self.allowed_image_types:
                    self.add_error(f"'data_type' has invalid value '{type_val}'. "
                                   f"Allowed: {self.allowed_image_types}", path)
            except (AttributeError, TypeError):
                self.add_error("'data_type' must be a string.", path)

    def _validate_sample(self, sample_group):
        """Placeholder for validating a 'sample_N' group (Sec A.15)."""
        # E.g., check that if 'unit_cell' exists, it has 6 floats.
        unit_cell = self._check_exists(sample_group, 'unit_cell', h5py.Dataset, required=False)
        if unit_cell:
            if unit_cell.shape != (6,):
                self.add_error(f"'unit_cell' must be an array of 6 floats.", sample_group.name)


    def _validate_axes(self, dset, is_modular=False):
        """
        Validates the 'axes' attribute of a dataset (Sec 9.1).
        This is a key part of validating scans.
        """
        path = dset.name
        if 'axes' not in dset.attrs:
            # Not always an error, implicit axes might apply.
            # Warn if dataset is high-dimensional.
            if dset.ndim > 2 and "data" in path:
                self.add_warning(
                    f"Dataset has {dset.ndim} dimensions but no 'axes' attribute to describe them.", path
                )
            return

        axes_attr = dset.attrs['axes']
        axes_names = axes_attr.split(':')

        if len(axes_names) != dset.ndim:
            self.add_error(
                f"'axes' attribute has {len(axes_names)} names, but dataset has {dset.ndim} dimensions.", path
            )
            return
        
        # Check for modular detector consistency
        if is_modular and axes_names[0] != 'module_identifier':
            self.add_warning(f"Modular data's 'axes' attribute should start with 'module_identifier'. "
                             f"Found '{axes_names[0]}'.", path)

        # Validate each dimension scale
        for i, axis_name in enumerate(axes_names):
            if axis_name in self.implicit_axes:
                continue

            axis_dset = self._check_exists(dset.parent, axis_name, h5py.Dataset)
            if axis_dset:
                # Dimension scale length must match data dimension size
                if isinstance(axis_dset[()], Sized) and not isinstance(axis_dset[()], bytes):
                    axis_len = len(axis_dset[()])
                else:
                    axis_len = axis_dset.shape[0] if axis_dset.ndim > 0 else 1
                
                if axis_len != dset.shape[i]:
                    self.add_error(
                        f"Dimension scale '{axis_name}' for axis {i} has length {axis_len}, "
                        f"but data dimension has size {dset.shape[i]}.", path
                    )

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="A validator for Coherent X-ray Imaging (CXI) files.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
This script checks a .cxi file against the format specification v1.6.
It verifies the presence of required groups/datasets, data types,
and the correctness of `axes` attributes for scans.

Example:
  python validate_cxi.py my_experiment.cxi
"""
    )
    parser.add_argument("filepath", help="Path to the CXI file to be validated.")
    args = parser.parse_args()

    validator = CXIValidator(args.filepath)
    is_valid = validator.validate()

    # Exit with a status code indicating success or failure
    sys.exit(0 if is_valid else 1)
