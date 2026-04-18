#FROM nvidia/cuda:12.1.1-cudnn8-devel-ubuntu22.04
FROM nvidia/cuda:13.2.0-cudnn-devel-ubuntu24.04

ARG USER=developer
ARG DEBIAN_FRONTEND=noninteractive

RUN apt update \
    && apt install -y --no-install-recommends \
       sudo git zsh curl wget ca-certificates \
       python3 python3-venv \
       libgl1 libglib2.0-0 \
    && apt clean \
    && apt autoremove -y \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -s /usr/bin/zsh ${USER} \
    && echo "${USER} ALL=(ALL) NOPASSWD: ALL" >/etc/sudoers.d/${USER} \
    && chmod 0440 /etc/sudoers.d/${USER}

USER ${USER}
ARG HOME=/home/${USER}
ARG ZSH=${HOME}/.oh-my-zsh
ARG ZSH_CUSTOM=${ZSH}/custom
WORKDIR ${HOME}

RUN <<EOT
    sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"
    mkdir -p ${ZSH_CUSTOM}
    git clone https://github.com/zsh-users/zsh-autosuggestions ${ZSH_CUSTOM}/plugins/zsh-autosuggestions
    git clone https://github.com/zsh-users/zsh-syntax-highlighting.git ${ZSH_CUSTOM}/plugins/zsh-syntax-highlighting
    sed -i.bak 's/plugins=(\(.*\))/plugins=(\1 zsh-autosuggestions zsh-syntax-highlighting)/' ~/.zshrc
EOT

ENV PATH="${HOME}/.local/bin:${PATH}"

RUN <<EOT
    curl -LsSf https://astral.sh/uv/install.sh | sh
    echo 'eval "$(uv generate-shell-completion zsh)"' >> ${HOME}/.zshrc
    echo 'eval "$(uvx --generate-shell-completion zsh)"' >> ${HOME}/.zshrc   
EOT

# Diretório padrão para quando o VS Code plugar no Dev Container
WORKDIR /workspaces/Assistente-Estudos