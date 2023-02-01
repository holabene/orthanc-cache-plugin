#!/bin/bash

# Specify the output directory and base file name
output_dir=../.data/test
base_file=image

# Create the output directory
mkdir -p ${output_dir}

# Generate study and series instance UID
StudyInstanceUID="1.2.3.$(date +%s)"
SeriesInstanceUID="1.2.4.$(date +%s)"

# Generate 100 dummy DICOM images
for i in $(seq -w 1 100); do
  output_file=${output_dir}/${base_file}${i}.dcm
  SOPInstanceUID="1.2.5.$i"

  cp test.dcm "${output_file}"

  dcmodify -nb \
  -i "InstanceNumber=$i" \
  -i "SOPInstanceUID=$SOPInstanceUID" \
  -i "SeriesInstanceUID=$SeriesInstanceUID" \
  -i "StudyInstanceUID=$StudyInstanceUID" \
  "${output_file}"
done
