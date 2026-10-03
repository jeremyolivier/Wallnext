// Full-screen slideshow: each picture slowly zooms and drifts (Ken Burns),
// then cross-fades into the next one.
import QtQuick

Rectangle {
    id: root
    color: "black"

    required property var pictures   // file URLs, already shuffled
    property int shown: 9000         // ms each picture stays
    property int fade: 1800          // ms of cross-fade
    property int next: 0

    component Slide: Image {
        id: slide
        anchors.fill: parent
        fillMode: Image.PreserveAspectCrop
        asynchronous: true
        smooth: true
        mipmap: true
        opacity: 0
        // Each slide drifts towards a random corner while zooming in.
        property real driftX: 0
        property real driftY: 0
        transform: [
            Scale {
                id: zoom
                origin.x: slide.width / 2
                origin.y: slide.height / 2
            },
            Translate { id: drift }
        ]
        function play() {
            driftX = (Math.random() - 0.5) * width * 0.06
            driftY = (Math.random() - 0.5) * height * 0.06
            kenBurns.restart()
        }
        ParallelAnimation {
            id: kenBurns
            NumberAnimation { target: zoom; properties: "xScale,yScale"; from: 1.0; to: 1.12; duration: root.shown + root.fade }
            NumberAnimation { target: drift; property: "x"; from: 0; to: slide.driftX; duration: root.shown + root.fade }
            NumberAnimation { target: drift; property: "y"; from: 0; to: slide.driftY; duration: root.shown + root.fade }
        }
        Behavior on opacity { NumberAnimation { duration: root.fade; easing.type: Easing.InOutQuad } }
    }

    Slide { id: a }
    Slide { id: b }
    property Item front: a

    function advance() {
        if (pictures.length === 0)
            return
        const back = front === a ? b : a
        back.source = pictures[next]
        next = (next + 1) % pictures.length
        back.play()
        back.z = 1
        front.z = 0
        back.opacity = 1
        front.opacity = 0
        front = back
    }

    Timer {
        interval: root.shown
        running: true
        repeat: true
        triggeredOnStart: true
        onTriggered: root.advance()
    }
}
