# This is your project's main settings file that can be committed to your
# repo. If you need to override a setting locally, use settings_local.py

#from funfactory.settings_base import *

# Bundles is a dictionary of two dictionaries, css and js, which list css files
# and js files that can be bundled together by the minify app.
MINIFY_BUNDLES = {
    'css': {
        'example_css': (
            'css/examples/main.css',
        ),
        'example_mobile_css': (
            'css/examples/mobile.css',
        ),
    },
    'js': {
        'example_js': (
            'js/examples/libs/jquery-1.4.4.min.js',
            'js/examples/libs/jquery.cookie.js',
            'js/examples/init.js',
        ),
    }
}


INSTALLED_APPS = [
    # Example code. Can (and should) be removed for actual projects.
    #'examples',

    'django.contrib.sessions',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.admin',
    'django.contrib.sites',
    'django.contrib.staticfiles',
    'systems',
    'mcsv',
    'invapi',
    'rest_framework',
    'rest_framework.authtoken',
    'django_filters',
    'reversion',
    'reversion_compare',
]



# Because Jinja2 is the default template loader, add any non-Jinja templated
# apps here:

DJANGO_TEMPLATE_APPS = [
    'admin',
    'build',
    'user_systems',
    ]
# Tells the extract script what files to look for L10n in and what function
# handles the extraction. The Tower library expects this.

# # Use this if you have localizable HTML files:
# DOMAIN_METHODS['lhtml'] = [
#    ('**/templates/**.lhtml',
#        'tower.management.commands.extract.extract_tower_template'),
# ]

# # Use this if you have localizable HTML files:
# DOMAIN_METHODS['javascript'] = [
#    # Make sure that this won't pull in strings from external libraries you
#    # may use.
#    ('media/js/**.js', 'javascript'),
# ]

# LOGGING = dict(loggers=dict(playdoh = {'level': logging.INFO}))
AUTH_PROFILE_MODULE = 'systems.UserProfile'
AUTHENTICATION_BACKENDS = (
        'django.contrib.auth.backends.RemoteUserBackend',
)
AUTH_PROFILE_MODULE = "systems.UserProfile"
PISTON_IGNORE_DUPE_MODELS = True

#TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'


#########################################################
#                   MOZ DNS                             #
#########################################################

JINJA_CONFIG = {'autoescape': False}
DEBUG_TOOLBAR_PANELS = (
    'debug_toolbar.panels.version.VersionDebugPanel',
    'debug_toolbar.panels.timer.TimerDebugPanel',
    'debug_toolbar.panels.settings_vars.SettingsVarsDebugPanel',
    'debug_toolbar.panels.headers.HeaderDebugPanel',
    'debug_toolbar.panels.request_vars.RequestVarsDebugPanel',
    'debug_toolbar.panels.template.TemplateDebugPanel',
    'debug_toolbar.panels.sql.SQLDebugPanel',
    'debug_toolbar.panels.signals.SignalDebugPanel',
    'debug_toolbar.panels.logger.LoggingPanel',
)
MIDDLEWARE = (
    'django.contrib.sessions.middleware.SessionMiddleware',
#    'django.middleware.locale.LocaleMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.RemoteUserMiddleware',
#    'reversion.middleware.RevisionMiddleware',
    #'debug_toolbar.middleware.DebugToolbarMiddleware',
)

INTERNAL_IPS = ('127.0.0.1','10.22.74.139','10.250.2.54')

def custom_show_toolbar(request): # pylint: disable=unused-argument
    return True # Always show toolbar, for example purposes only.

BUG_URL = 'https://bugzilla.mozilla.org/show_bug.cgi?id='

DEBUG_TOOLBAR_CONFIG = {
    'INTERCEPT_REDIRECTS': False,
    'SHOW_TOOLBAR_CALLBACK': custom_show_toolbar,
    'HIDE_DJANGO_SQL': False,
    'TAG': 'div',
    'ENABLE_STACKTRACES' : True,
}

#############################################################
#                       MOZ DNS                             #
#############################################################
#from settings.dnsbuilds import *
MOZDNS_BASE_URL = "/mozdns"
CORE_BASE_URL = "/core"
ROOT_URLCONF = 'urls'
BUILD_PATH = '/home/juber/dnsbuilds/'

# HACK HACK This will need to be fixed
from settings.local import DATABASES, REST_FRAMEWORK, TEMPLATES, ALLOWED_HOSTS  # pylint: disable=unused-import
