import QtQuick
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
    tooltipText: "LazyBlend"
    onPressed: function(button) {
      if (!root.bar) return
      root.bar.run("omarchy-launch terminal lazyblend")
    }
  }
}
