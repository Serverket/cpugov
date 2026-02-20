# SPDX-License-Identifier: GPL-3.0-or-later
project('cpugov',
  version: '0.1.1',
  meson_version: '>= 0.62.0',
  default_options: [
    'warning_level=2',
  ],
)

i18n = import('i18n')
gnome = import('gnome')
python = import('python')

py_installation = python.find_installation('python3')

app_id = 'io.github.serverket.cpugov'
gettext_package = meson.project_name()

prefix = get_option('prefix')
bindir = prefix / get_option('bindir')
datadir = prefix / get_option('datadir')
pkgdatadir = datadir / meson.project_name()
libexecdir = prefix / get_option('libexecdir')
sysconfdir = get_option('sysconfdir')

conf = configuration_data()
conf.set('APP_ID', app_id)
conf.set('VERSION', meson.project_version())
conf.set('PYTHON', py_installation.full_path())
conf.set('LOCALE_DIR', datadir / 'locale')
conf.set('PKGDATADIR', pkgdatadir)
conf.set('PREFIX', prefix)
conf.set('BINDIR', bindir)
conf.set('LIBEXECDIR', libexecdir)

subdir('data')
if get_option('daemon')
  subdir('daemon')
endif
subdir('src')
subdir('po')
