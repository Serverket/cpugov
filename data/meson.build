# Data meson.build
# SPDX-License-Identifier: GPL-3.0-or-later

# Desktop file
desktop_file = i18n.merge_file(
  input: 'io.github.serverket.cpugov.desktop',
  output: 'io.github.serverket.cpugov.desktop',
  type: 'desktop',
  po_dir: meson.project_source_root() / 'po',
  install: true,
  install_dir: datadir / 'applications',
)

# Validate desktop file
desktop_utils = find_program('desktop-file-validate', required: false)
if desktop_utils.found()
  test('Validate desktop file', desktop_utils,
    args: [desktop_file]
  )
endif

# AppStream metainfo
metainfo_file = i18n.merge_file(
  input: 'io.github.serverket.cpugov.metainfo.xml',
  output: 'io.github.serverket.cpugov.metainfo.xml',
  po_dir: meson.project_source_root() / 'po',
  install: true,
  install_dir: datadir / 'metainfo',
)

# Validate metainfo
appstreamcli = find_program('appstreamcli', required: false)
if appstreamcli.found()
  test('Validate appstream file', appstreamcli,
    args: ['validate', '--no-net', '--explain', metainfo_file]
  )
endif

# GSettings schema
install_data(
  'io.github.serverket.cpugov.gschema.xml',
  install_dir: datadir / 'glib-2.0' / 'schemas',
)

# Compile schemas for testing
gnome.compile_schemas(depend_files: 'io.github.serverket.cpugov.gschema.xml')

# D-Bus system bus config (must go to /etc, not $datadir)
if get_option('daemon')
  install_data(
    'io.github.serverket.cpugov.conf',
    install_dir: '/etc' / 'dbus-1' / 'system.d',
  )

  # Polkit policy
  install_data(
    'io.github.serverket.cpugov.policy',
    install_dir: datadir / 'polkit-1' / 'actions',
  )
endif

# Icon
install_data(
  'io.github.serverket.cpugov.svg',
  install_dir: datadir / 'icons' / 'hicolor' / 'scalable' / 'apps',
)
