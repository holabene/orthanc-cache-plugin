#!/bin/bash

# Script directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

# Specify the output directory and base file name
output_dir="${DIR}/../.data/test"
base_file=image

# Number of series and images per series (default: 1 series with 100 images)
num_series=${1:-1}
num_images=${2:-100}

# Create the output directory
mkdir -p "${output_dir}"

# Generate study instance UID
StudyInstanceUID="1.2.3.$(date +%s)"

# Generate array of objects with DICOM file path
files=()

for (( s=1; s<=num_series; s++ )); do
  # Generate series instance UID
  SeriesInstanceUID="1.2.4.$(date +%s).${s}"

  for (( i=1; i<=num_images; i++ )); do
    # Generate file path, SOP instance UID, and object for JSON array
    output_file="${output_dir}/series-${s}/${base_file}${i}.dcm"
    SOPInstanceUID="1.2.5.${s}.${i}"

    # Create directory for series if it doesn't exist
    mkdir -p "$(dirname "$output_file")"

    # Copy and modify template DICOM file
    cp "${DIR}/test.dcm" "${output_file}"
    dcmodify -nb \
      -i "InstanceNumber=$i" \
      -i "SOPInstanceUID=$SOPInstanceUID" \
      -i "SeriesInstanceUID=$SeriesInstanceUID" \
      -i "StudyInstanceUID=$StudyInstanceUID" \
      "${output_file}"

    # Add file path and series information to JSON array
    files+=("{\"path\":\"${output_file}\"}")
  done
done

find "${output_dir}" -name "*.dcm" -type f | jq -R . | jq -s . > "${output_dir}/files.json"
