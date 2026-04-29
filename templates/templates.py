import socket

def get_ip_address():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]


def get_plain_template():
    return f"Your MTS server is down at IP: {get_ip_address()}"


def get_html_template():
    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Container Alert</title>
</head>
<body style="margin: 0; padding: 20px; background-color: #f8f9fa; font-family: Arial, Helvetica, sans-serif;">
    <table role="presentation" width="100%" border="0" cellpadding="0" cellspacing="0">
        <tr>
            <td align="center" style="padding: 40px 0;">
                <table role="presentation" width="100%" style="max-width: 600px; background-color: #ffebee; border: 2px solid #ef5350; border-radius: 8px;">
                    <tr>
                        <td align="center" style="padding: 24px 32px; color: #c62828; font-size: 18px; font-weight: bold; line-height: 1.4; font-family: Arial, Helvetica, sans-serif;">
                            Your MTS server is down at IP: {get_ip_address()}
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""
