from time import sleep

from machine import reset, soft_reset
from micropython import const
from uos import listdir, mkdir, remove, rmdir
from ubinascii import b2a_base64

from pico_lte.utils.atcom import ATCom
from pico_lte.utils.status import Status
from pico_lte.core import PicoLTE
from pico_lte.common import debug

F_BUFFER = const(64)

picoLTE = PicoLTE()
atcom = ATCom()

picoLTE.network.register_network()
picoLTE.http.set_context_id()
picoLTE.network.get_pdp_ready()


def check_version(host, project, auth=None, timeout=5) -> tuple[bool, str]:
    current_version = ""
    if "version" in listdir():
        with open("version", "r") as current_version_file:
            current_version = current_version_file.readline().strip()

    filepath = f"{project}/version"
    url = f"http://{host}/{filepath}"
    picoLTE.http.set_server_url(url=url)

    if auth:
        return False, current_version
        # response = get(
        #     f"{host}/{project}/version",
        #     headers={"Authorization": f"Basic {auth}"},
        #     timeout=timeout,
        # )
    else:
        HEADER = "\r\n".join(
            [
                f"GET /{filepath} HTTP/1.1",
                f"Host: {host}",
                "\r\n",
            ]
        )
        debug.debug(HEADER)
        result = picoLTE.http.get(HEADER, header_mode=1, timeout=timeout)
        debug.debug("Get result:", result)

    sleep(5)

    result = picoLTE.http.read_response()
    debug.debug(result)
    if result["status"] != Status.SUCCESS:
        debug.error(result["status"])
        return False, current_version

    response_text = result["response"]
    debug.debug("response:", response_text)
    remote_version = response_text[0].strip()
    debug.debug("Remote version:", remote_version)
    return current_version != remote_version, remote_version


def generate_auth(user=None, passwd=None) -> str | None:
    if not user and not passwd:
        return None
    if (user and not passwd) or (passwd and not user):
        raise ValueError("User err")
    auth_bytes = b2a_base64(f"{user}:{passwd}".encode())
    return auth_bytes.decode().strip()


def ota_update(
    host,
    project,
    filenames,
    ext_src="py",
    ext_tar="py",
    use_version_prefix=True,
    user=None,
    passwd=None,
    hard_reset_device=True,
    soft_reset_device=False,
    timeout=5,
) -> None:
    all_files_found = True
    auth = generate_auth(user, passwd)
    prefix_or_path_separator = "_" if use_version_prefix else "/"

    _version_changed, _remote_version = check_version(
        host, project, auth=auth, timeout=timeout
    )
    debug.info(
        f"Version changed: {_version_changed}, Remote version: {_remote_version}"
    )

    if _version_changed:
        try:
            mkdir("tmp")
        except OSError:
            pass

        for filename in filenames:
            _filepath = f"{project}/{_remote_version}{prefix_or_path_separator}{filename}.{ext_src}"
            _url = f"http://{host}/{_filepath}"
            picoLTE.http.set_server_url(url=_url)

            if auth:
                return
                # response = get(
                #     f"{host}/{project}/{remote_version}{prefix_or_path_separator}{filename}.{ext_src}",
                #     headers={"Authorization": f"Basic {auth}"},
                #     timeout=timeout,
                # )
            else:
                _HEADER = "\r\n".join(
                    [
                        f"GET /{_filepath} HTTP/1.1",
                        f"Host: {host}",
                        "\r\n",
                    ]
                )
                debug.debug(_HEADER)
                _result = picoLTE.http.get(_HEADER, header_mode=1, timeout=timeout)
                debug.info("Get result:", _result)

            sleep(5)

            _file_handle = 1

            _result = picoLTE.http.read_response_to_file(f'"{filename}"')
            debug.info("Read to file:", _result)

            _result = atcom.send_at_comm(f'AT+QFOPEN="{filename}",0')
            debug.info("open:", _result)

            with open(f"tmp/{filename}", "w") as out_file:
                while True:
                    _command = f"AT+QFREAD={_file_handle},{F_BUFFER}"
                    _result = atcom.send_at_comm(_command)
                    debug.debug(_result)
                    if _result["status"] != Status.SUCCESS:
                        break
                    else:
                        _response = _result["response"]
                        _data = _response[1]
                        out_file.write(_data)
                out_file.flush()
                out_file.close()

            _command = f"AT+QFCLOSE={_file_handle}"
            _result = atcom.send_at_comm(_command)
            debug.info("close:", _result)

        if all_files_found:
            for file in filenames:
                _tmp = f"tmp/{file}"

                _tar = f"{file}.{ext_tar}"

                with open(_tmp, "r") as src, open(_tar, "w") as tar:
                    while True:
                        _data = src.read(F_BUFFER)
                        if not _data:
                            break
                        tar.write(_data)
                remove(f"tmp/{file}")
            try:
                rmdir("tmp")
            except OSError:
                pass

            with open("version", "w") as current_version_file:
                current_version_file.write(_remote_version)

            if soft_reset_device:
                print("Soft-resetting device...")
                soft_reset()
            if hard_reset_device:
                print("Hard-resetting device...")
                reset()


def check_for_ota_update(
    host, project, user=None, passwd=None, timeout=5, soft_reset_device=False
):
    auth = generate_auth(user, passwd)
    version_changed, remote_version = check_version(
        host, project, auth=auth, timeout=timeout
    )
    if version_changed:
        if soft_reset_device:
            print(f"Found new version {remote_version}, soft-resetting device...")
            soft_reset()
        else:
            print(f"Found new version {remote_version}, hard-resetting device...")
            reset()
