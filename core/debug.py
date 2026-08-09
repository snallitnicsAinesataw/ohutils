# FOR DEBUG ONLY...?
from .config import Config, setGlobalConfig, getGlobalConfig
debug_config = Config.fromDict({'noStartEnd':False, 'verbose':True,'fileName':'TESTFILE_ob%i.obarc'})
debug_set_config = lambda: setGlobalConfig(debug_config)
debug_print_config = lambda end="\n": print(getGlobalConfig(),end=end)