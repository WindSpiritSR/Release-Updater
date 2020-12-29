# Usage

## Use python

```shell
python /path/to/release_updater.py
```

## or you can create a shell script to run it at crontab

> update_release.sh

```shell
#!/bin/bash
cd /path/to/release_updater/
python /path/to/release_updater.py

# If you want someone else use these release file
# chown user:user -R /path/to/release_file/
# chmod 755 -R /path/to/release_file/
```

> crontab

```shell
0 2 * * *       /path/to/update_release.sh
```
