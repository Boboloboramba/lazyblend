import Quickshell
import Quickshell.Io
import QtQuick
import QtQuick.Layouts

Text {
  id: root

  property string tooltipText: "LazyBlend - Blender file browser"

  text: "\uf2d2"  // Blender nerd font icon
  font.family: "Symbols Nerd Font"
  font.pixelSize: 16
  color: MouseArea.containsMouse ? palette.highlight : palette.text

  MouseArea {
    id: mouseArea
    anchors.fill: parent
    hoverEnabled: true
    cursorShape: Qt.PointingHandCursor
    onClicked: {
      lazyblendProc.running = true
    }
  }

  Process {
    id: lazyblendProc
    command: ["omarchy-launch", "terminal", "lazyblend"]
    running: false
  }

  ToolTip {
    visible: mouseArea.containsMouse
    text: root.tooltipText
  }
}
