# Here is an example of how to use the orthanc_cache_plugin module in a Python script:
#
# Define this script in orthanc.json:
# {
#  "PythonScript" : "/tmp/example.py"
# }
#
# More information see https://book.orthanc-server.com/plugins/python.html

import sys

# Add the directory containing the orthanc_cache_plugin module to the Python path
# Here the path is /usr/share/orthanc/plugins/orthanc_cache_plugin
# as defined in docker-compose.yml
sys.path.append('/usr/share/orthanc/plugins/')

# Import the enable_cache_plugin function
from orthanc_cache_plugin import enable_cache_plugin

enable_cache_plugin()