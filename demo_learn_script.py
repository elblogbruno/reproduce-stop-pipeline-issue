#!/usr/bin/env python3
import time
import depthai as dai

# Start defining a pipeline
pipeline = dai.Pipeline()

# Define a source - color camera
cam = pipeline.create(dai.node.ColorCamera)

cam_out = pipeline.createXLinkOut()
cam_out.setStreamName("cam_out")
cam_out.input.setQueueSize(1)
cam.video.link(cam_out.input)
    
# Script node
script = pipeline.create(dai.node.Script)

print("Creating SPI in node...")
spiIn = pipeline.create(dai.node.SPIIn)
spiIn.setStreamName("spimetain")
spiIn.setBusId(0)
spiIn.out.link(script.inputs['spimetain'])

script.setScript("""
    import json
    import time

    calc = False

    data = dict()
    ctrl = CameraControl()
    
    while not data: 
        node.warn("Waiting for esp32 to start")
        data = node.io['spimetain'].get().getData()

        result = dict([("started", 'true')])
        b = Buffer(30)
        b.setData(json.dumps(result).encode('utf-8'))
        node.io['host'].send(b)

    jsonStr = str(data, 'utf-8')
    msg_dict = json.loads(jsonStr)
    node.warn (f"Esp32 is alive: {msg_dict}")

    while True:
        data = node.io['spimetain'].get().getData()
        node.warn (str(len(data)) + " bytes received")

        jsonStr = str(data, 'utf-8')
        msg_dict = json.loads(jsonStr)
        node.warn (f"Manager received: {msg_dict}")

        if msg_dict['action'] == 'stop':
            node.warn ("Stop")
            
            result = dict([("stopped", 'true')])
            b = Buffer(30)
            b.setData(json.dumps(result).encode('utf-8'))
            node.io['host'].send(b)

            ctrl.setStopStreaming()
            node.io['out'].send(ctrl)

            calc = False

        elif msg_dict['action'] == 'start':
            node.warn ("Start")
            
            result = dict([("started", 'true')])
            b = Buffer(30)
            b.setData(json.dumps(result).encode('utf-8'))
            node.io['host'].send(b)

            ctrl.setStartStreaming()
            node.io['out'].send(ctrl)

            calc = True
        elif msg_dict['action'] == 'ack':
            node.warn("MCU RECEIVED OUR DATA")
        
            if calc:
                node.warn(f"calc") 

                result = dict([("loop", 'true')])
                b = Buffer(30)
                b.setData(json.dumps(result).encode('utf-8'))
                node.io['host'].send(b)      
""")

spiOut = pipeline.create(dai.node.SPIOut)
spiOut.setStreamName("spimetaout")
spiOut.setBusId(0)
spiOut.input.setBlocking(False)

print("Creating SPI out node...")
script.outputs['host'].link(spiOut.input)

# Connections
script.outputs['out'].link(cam.inputControl)

# Connect to device with pipeline
with dai.Device(pipeline) as device:
    while not device.isClosed():
        time.sleep(1)
