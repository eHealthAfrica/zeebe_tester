# zeebe_tester
Tools For Developing Zeebe Workflows and Workers using the Stream Consumer.

The following are packaged:
 - Zeebe Broker
 - Zeebe Simple Monitor (localhost:8082) 
 - Aether Stream Consumer (localhost:9013)
 - Zeebe Tester (this app)

Zeebe Tester keeps a file system in sync with a Stream Consumer. While Tester is running, if you modify or add an artifact to the filesystem (./assets) it will be reflected automatically in the consumer. Likewise, if you save changes to a BPMN it will be updated in the broker. 

Download the Zeebe Modeler if you want to edit the BPMNs:
https://github.com/zeebe-io/zeebe-modeler


To start:
`scripts/up.sh`

To wipe the broker and consumer (your artifact changes will stay unless you revert those with git)
`scripts/wipe.sh`


Demo:

There are some interesting arifacts included in the package. 

Start everything with:
- `scripts/up.sh`
Visit the simple monitor.
 - Zeebe Simple Monitor (localhost:8082) 
 - Look at the workflows (http://localhost:8082/views/workflows)
 - We'll be drivin the `http-getter` instance.
 - Click the "workflow-key" link to view it.

This workflow starts on a message sent to it giving it instructions, does work on an interval until it gets a second message telling it to stop.

The thing doing the work is a job/pipeline in the Stream Consumer.
`/assets/job/rest_handler.json`
&
`/assets/resource/pipeline/rest_handler.json`
which uses: a `restcall` and a `zeebecomplete` transformation.

Don't worry, you can modify any of these things, break it and put it back together.

This workflow is waiting for a message to kick it off. We have some samples in `/messages`

In worker-start.json
```
{
  "listener_name": "trigger-worker",
  "variables": {
    "worker_id":"one",
    "url": "http://www3.septa.org/hackathon/TransitViewAll/",
    "method": "get",
    "period": "R/PT10S"
  }
}
```
using `httpie` you can start it up with:
```
http --json POST http://localhost:9013/zeebe/send_message?id=default -a admin:password < ./messages/worker-start.json
```

Now look at instances again:
http://localhost:8082/views/instances
Click on the instance to watch it work.
Take a look at the context and audit log. Sweet.

When you want to send the stop message (to the cancel-worker node on the diagram) we'll send the broker worker-cancel.json
```
{
  "listener_name": "cancel-worker",
  "correlationKey": "one"
}
```

again with `httpie`
```
http --json POST http://localhost:9013/zeebe/send_message?id=default -a admin:password < ./messages/worker-cancel.json 

```
