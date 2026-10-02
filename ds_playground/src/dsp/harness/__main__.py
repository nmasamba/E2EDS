import sys

from dsp.harness.instance import home, serve

serve(home(), dev=sys.argv[1:] == ["--dev"])
