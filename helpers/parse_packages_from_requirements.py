import re


def parse_git_package_link(link: str) -> list:
    """
    Convert link "git+https://gitlab.2gis.ru/ugc/kafka_client@0.21.2" to ["kafka_client", "0.21.2"]
    or "kafka-client @ git+https://gitlab.2gis.ru/ugc/kafka_client@0.21.2" to ["kafka_client", "0.21.2"]
    """
    link_elements = link.split('/')

    if len(link_elements) > 0:
        last_link_element = link_elements[-1]
    else:
        return list()

    if '@' in last_link_element:
        package_info = last_link_element.split('@', 1)
    else:
        return list([last_link_element])

    return package_info


def parse_packages_info_from_requirements_txt(file_content: str) -> dict:
    requirements_dict = dict()
    lines = file_content.splitlines()

    for line in lines:
        line = line.strip()

        if not line or line.startswith('#') or line.startswith('--'):
            continue

        if 'git+' in line:
            package_info = parse_git_package_link(line)
        else:
            package_info = re.split(r'==', line, 1)

        len_package_info = len(package_info)

        if len_package_info == 1:
            requirements_dict[package_info[0]] = None
        elif len_package_info == 2:
            requirements_dict[package_info[0]] = package_info[1]

    return requirements_dict
