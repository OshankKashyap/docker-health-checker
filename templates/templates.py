import socket


def get_ip_address():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]


def get_plain_template():
    return f"Your MTS server is down at IP: {get_ip_address()}"


def get_plain_up_template(downtime: str):
    return f"Your MTS server is back up at IP: {get_ip_address()} after {downtime} of downtime."


def get_html_template():
    ip = get_ip_address()
    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Container Alert — Server Down</title>
</head>
<body style="margin: 0; padding: 0; background-color: #0f0f0f; font-family: 'Courier New', Courier, monospace;">
    <table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0"
           style="min-height: 100vh; background-color: #0f0f0f;">
        <tr>
            <td align="center" style="padding: 48px 20px;">

                <!-- Outer card -->
                <table role="presentation" width="100%"
                       style="max-width: 580px; background-color: #1a0000;
                              border: 1px solid #ff3333;
                              border-radius: 4px;
                              box-shadow: 0 0 32px rgba(255,51,51,0.25), 0 0 2px #ff3333;">

                    <!-- Header bar -->
                    <tr>
                        <td style="background-color: #ff2222; padding: 12px 28px;
                                   border-radius: 3px 3px 0 0;">
                            <table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td style="color: #fff; font-size: 11px; font-weight: bold;
                                               letter-spacing: 3px; text-transform: uppercase;
                                               font-family: 'Courier New', Courier, monospace;">
                                        &#9632;&nbsp;&nbsp;CRITICAL ALERT
                                    </td>
                                    <td align="right" style="color: rgba(255,255,255,0.6);
                                                             font-size: 10px;
                                                             font-family: 'Courier New', Courier, monospace;">
                                        MTS MONITOR
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Body -->
                    <tr>
                        <td style="padding: 36px 28px 28px;">

                            <!-- Big status label -->
                            <table role="presentation" border="0" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td style="background-color: #ff2222; border-radius: 2px;
                                               padding: 4px 10px; margin-bottom: 24px; display: inline-block;">
                                        <span style="color: #fff; font-size: 10px; font-weight: bold;
                                                     letter-spacing: 2px;
                                                     font-family: 'Courier New', Courier, monospace;">
                                            STATUS: OFFLINE
                                        </span>
                                    </td>
                                </tr>
                            </table>

                            <div style="height: 20px;"></div>

                            <!-- Main message -->
                            <p style="margin: 0 0 8px 0; color: #ff6666; font-size: 22px;
                                      font-weight: bold; line-height: 1.3;
                                      font-family: 'Courier New', Courier, monospace;">
                                Server is down
                            </p>
                            <p style="margin: 0 0 28px 0; color: #aaaaaa; font-size: 13px; line-height: 1.6;
                                      font-family: 'Courier New', Courier, monospace;">
                                Your MTS server has become unreachable.<br>
                                Immediate attention is required.
                            </p>

                            <!-- Divider -->
                            <table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td style="border-top: 1px solid #330000; padding-bottom: 24px;"></td>
                                </tr>
                            </table>

                            <!-- IP row -->
                            <table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0"
                                   style="background-color: #110000; border: 1px solid #330000;
                                          border-radius: 3px;">
                                <tr>
                                    <td style="padding: 14px 18px;">
                                        <span style="color: #666; font-size: 10px; letter-spacing: 2px;
                                                     text-transform: uppercase; display: block; margin-bottom: 4px;
                                                     font-family: 'Courier New', Courier, monospace;">
                                            Server IP
                                        </span>
                                        <span style="color: #ff4444; font-size: 16px; font-weight: bold;
                                                     letter-spacing: 1px;
                                                     font-family: 'Courier New', Courier, monospace;">
                                            {ip}
                                        </span>
                                    </td>
                                </tr>
                            </table>

                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="padding: 14px 28px; border-top: 1px solid #220000;">
                            <span style="color: #444; font-size: 10px; letter-spacing: 1px;
                                         font-family: 'Courier New', Courier, monospace;">
                                Automated alert &mdash; MTS Health Monitor
                            </span>
                        </td>
                    </tr>

                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""


def get_html_up_template(downtime: str):
    ip = get_ip_address()
    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Container Alert — Server Restored</title>
</head>
<body style="margin: 0; padding: 0; background-color: #0a0f0a; font-family: 'Courier New', Courier, monospace;">
    <table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0"
           style="min-height: 100vh; background-color: #0a0f0a;">
        <tr>
            <td align="center" style="padding: 48px 20px;">

                <!-- Outer card -->
                <table role="presentation" width="100%"
                       style="max-width: 580px; background-color: #001a04;
                              border: 1px solid #22cc44;
                              border-radius: 4px;
                              box-shadow: 0 0 32px rgba(34,204,68,0.2), 0 0 2px #22cc44;">

                    <!-- Header bar -->
                    <tr>
                        <td style="background-color: #18a832; padding: 12px 28px;
                                   border-radius: 3px 3px 0 0;">
                            <table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td style="color: #fff; font-size: 11px; font-weight: bold;
                                               letter-spacing: 3px; text-transform: uppercase;
                                               font-family: 'Courier New', Courier, monospace;">
                                        &#9632;&nbsp;&nbsp;RECOVERY NOTICE
                                    </td>
                                    <td align="right" style="color: rgba(255,255,255,0.6);
                                                             font-size: 10px;
                                                             font-family: 'Courier New', Courier, monospace;">
                                        MTS MONITOR
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Body -->
                    <tr>
                        <td style="padding: 36px 28px 28px;">

                            <!-- Status label -->
                            <table role="presentation" border="0" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td style="background-color: #18a832; border-radius: 2px;
                                               padding: 4px 10px;">
                                        <span style="color: #fff; font-size: 10px; font-weight: bold;
                                                     letter-spacing: 2px;
                                                     font-family: 'Courier New', Courier, monospace;">
                                            STATUS: ONLINE
                                        </span>
                                    </td>
                                </tr>
                            </table>

                            <div style="height: 20px;"></div>

                            <!-- Main message -->
                            <p style="margin: 0 0 8px 0; color: #44ee66; font-size: 22px;
                                      font-weight: bold; line-height: 1.3;
                                      font-family: 'Courier New', Courier, monospace;">
                                Server is back up
                            </p>
                            <p style="margin: 0 0 28px 0; color: #aaaaaa; font-size: 13px; line-height: 1.6;
                                      font-family: 'Courier New', Courier, monospace;">
                                Your MTS server has been successfully restored.<br>
                                Normal operations have resumed.
                            </p>

                            <!-- Divider -->
                            <table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0">
                                <tr>
                                    <td style="border-top: 1px solid #002208; padding-bottom: 24px;"></td>
                                </tr>
                            </table>

                            <!-- IP + Downtime rows -->
                            <table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0"
                                   style="background-color: #010f03; border: 1px solid #003308;
                                          border-radius: 3px;">
                                <tr>
                                    <td style="padding: 14px 18px; border-bottom: 1px solid #003308;">
                                        <span style="color: #666; font-size: 10px; letter-spacing: 2px;
                                                     text-transform: uppercase; display: block; margin-bottom: 4px;
                                                     font-family: 'Courier New', Courier, monospace;">
                                            Server IP
                                        </span>
                                        <span style="color: #33dd55; font-size: 16px; font-weight: bold;
                                                     letter-spacing: 1px;
                                                     font-family: 'Courier New', Courier, monospace;">
                                            {ip}
                                        </span>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding: 14px 18px;">
                                        <span style="color: #666; font-size: 10px; letter-spacing: 2px;
                                                     text-transform: uppercase; display: block; margin-bottom: 4px;
                                                     font-family: 'Courier New', Courier, monospace;">
                                            Total Downtime
                                        </span>
                                        <span style="color: #ffcc44; font-size: 16px; font-weight: bold;
                                                     letter-spacing: 1px;
                                                     font-family: 'Courier New', Courier, monospace;">
                                            {downtime}
                                        </span>
                                    </td>
                                </tr>
                            </table>

                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="padding: 14px 28px; border-top: 1px solid #002208;">
                            <span style="color: #444; font-size: 10px; letter-spacing: 1px;
                                         font-family: 'Courier New', Courier, monospace;">
                                Automated alert &mdash; MTS Health Monitor
                            </span>
                        </td>
                    </tr>

                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""
