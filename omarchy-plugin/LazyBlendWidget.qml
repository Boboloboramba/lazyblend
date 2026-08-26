import QtQuick
import qs.Ui

BarWidget {
  id: root
  moduleName: "io.github.Boboloboramba.lazyblend"

  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  WidgetButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: "\uDB84\uDD72"
    horizontalMargin: 7.5
    tooltipText: "LazyBlend - Blender file browser"
    onPressed: function(button) {
      if (!root.bar) return
      root.bar.run("uwsm-app -- xdg-terminal-exec -e lazyblend")
    }
  }
}
