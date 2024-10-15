# MXHunt

## Description
MXHunt is a tool that helps you find mail exchanger records related to a domain. It is useful for penetration testers and bug hunters who want to find out the mail exchanger records of a domain for reconnaissance purposes.

## Installation
```bash
pipx install git+https://github.com/minniear/MXHunt.git
```

## Usage
```bash
usage: mxhunt [-h] [-r RATE] [-q] (-d DOMAIN | -f FILE) [-o OUTPUT]

options:
  -h, --help            show this help message and exit
  -r RATE, --rate RATE  Rate limit of concurrent connections (default: 10)
  -q, --quiet           Quiet mode, do not output mail servers

Input Options:
  -d DOMAIN, --domain DOMAIN
                        Domain to check
  -f FILE, --file FILE  A file with domains to check

Output Options:
  -o OUTPUT, --output OUTPUT
                        Report output base name (default: mx_report)
```

## Example
![Example](./example.png)