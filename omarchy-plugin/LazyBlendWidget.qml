import QtQuick
import Quickshell.Io
import qs.Ui

BarWidget {
  id: root
  moduleName: "lazyblend"

  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  WidgetButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: "\uDB84\uDD72"
    horizontalMargin: 7.5
    tooltipText: "LazyBlend - Blender file browser"
    font.family: "Symbols Nerd Font"
    onPressed: function(button) {
      lazyblendProc.running = true
    }
  }

  Process {
    id: lazyblendProc
    command: ["uwsm-app", "--", "xdg-terminal-exec", "-e", "lazyblend"]
    running: false
  }
}
