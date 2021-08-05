# =============================================================================
# Author: Xianyuan Liu, xianyuan.liu@outlook.com
# =============================================================================

"""
Define the feature extractor for video including I3D, R3D_18, MC3_18 and R2PLUS1D_18 w/o SELayers.
"""

import logging

from kale.embed.video_i3d import i3d_joint
from kale.embed.video_res3d import mc3, r2plus1d, r3d
from kale.embed.video_se_i3d import se_i3d_joint
from kale.embed.video_se_res3d import se_mc3, se_r2plus1d, se_r3d
from kale.embed.video_ta3n import ta3n_joint
from kale.loaddata.video_access import get_image_modality


def get_extractor_video(model_name, image_modality, attention, dict_num_classes):
    """Get the feature extractor w/o the pre-trained model and SELayers for original image input.
    The pre-trained models are saved in the path ``$XDG_CACHE_HOME/torch/hub/checkpoints/``.
    For Linux, default path is ``~/.cache/torch/hub/checkpoints/``.
    For Windows, default path is ``C:/Users/$USER_NAME/.cache/torch/hub/checkpoints/``.
    Provide four pre-trained models: "rgb_imagenet", "flow_imagenet", "rgb_charades", "flow_charades".

    Args:
        model_name (string): The name of the feature extractor. (Choices=["I3D", "R3D_18", "R2PLUS1D_18", "MC3_18"])
        image_modality (string): Image type. (Choices=["rgb", "flow", "joint"])
        attention (string): The attention type. (Choices=["SELayerC", "SELayerT", "SELayerCoC", "SELayerMC", "SELayerCT", "SELayerTC", "SELayerMAC"])
        dict_num_classes (dict): The dictionary of class number for specific dataset.

    Returns:
        feature_network (dictionary): The network to extract features.
        class_feature_dim (int): The dimension of the feature network output for ClassNet.
                            It is a convention when the input dimension and the network is fixed.
        domain_feature_dim (int): The dimension of the feature network output for DomainNet.
    """
    rgb, flow, audio = get_image_modality(image_modality)
    # only use verb class when input is image.
    num_classes = dict_num_classes["verb"]

    attention_list = ["SELayerC", "SELayerT", "SELayerCoC", "SELayerMC", "SELayerCT", "SELayerTC", "SELayerMAC"]
    model_list = ["I3D", "R3D_18", "MC3_18", "R2PLUS1D_18"]

    if attention in attention_list:
        att = True
    elif attention == "None":
        att = False
    else:
        raise ValueError("Wrong MODEL.ATTENTION. Current: {}".format(attention))

    if model_name not in model_list:
        raise ValueError("Wrong MODEL.METHOD. Current:{}".format(model_name))

    if "TA3N" in model_name:
        rgb_pretrained = flow_pretrained = audio_pretrained = None
        class_feature_dim = 0
        domain_feature_dim = 1024
        if rgb:
            rgb_pretrained = "rgb_ta3n"
            class_feature_dim += domain_feature_dim
        if flow:
            flow_pretrained = "flow_ta3n"
            class_feature_dim += domain_feature_dim
        if audio:
            audio_pretrained = "audio_ta3n"
            class_feature_dim += domain_feature_dim
        feature_network = ta3n_joint(rgb_pretrained, flow_pretrained, audio_pretrained, input_size=1024,
                                     input_type="image", dict_n_class=num_classes)
        return feature_network, int(class_feature_dim), int(domain_feature_dim)

    # Get I3D w/o SELayers for RGB, Flow or joint input
    if model_name == "I3D":
        rgb_pretrained_model = flow_pretrained_model = None
        if rgb:
            rgb_pretrained_model = "rgb_imagenet"  # Options=["rgb_imagenet", "rgb_charades"]
        if flow:
            flow_pretrained_model = "flow_imagenet"  # Options=["flow_imagenet", "flow_charades"]

        if rgb and flow:
            class_feature_dim = 2048
            domain_feature_dim = class_feature_dim / 2
        else:
            class_feature_dim = 1024
            domain_feature_dim = class_feature_dim

        if not att:
            logging.info("{} without SELayer.".format(model_name))
            feature_network = i3d_joint(
                rgb_pt=rgb_pretrained_model, flow_pt=flow_pretrained_model, num_classes=num_classes, pretrained=True
            )
        else:
            logging.info("{} with {}.".format(model_name, attention))
            feature_network = se_i3d_joint(
                rgb_pt=rgb_pretrained_model,
                flow_pt=flow_pretrained_model,
                attention=attention,
                num_classes=num_classes,
                pretrained=True,
            )

    # Get R3D_18/R2PLUS1D_18/MC3_18 w/o SELayers for RGB, Flow or joint input
    elif model_name in ["R3D_18", "R2PLUS1D_18", "MC3_18"]:
        if rgb and flow:
            class_feature_dim = 1024
            domain_feature_dim = class_feature_dim / 2
        else:
            class_feature_dim = 512
            domain_feature_dim = class_feature_dim

        if model_name == "R3D_18":
            if not att:
                logging.info("{} without SELayer.".format(model_name))
                feature_network = r3d(rgb=rgb, flow=flow, pretrained=True)
            else:
                logging.info("{} with {}.".format(model_name, attention))
                feature_network = se_r3d(rgb=rgb, flow=flow, pretrained=True, attention=attention)

        elif model_name == "R2PLUS1D_18":
            if not att:
                logging.info("{} without SELayer.".format(model_name))
                feature_network = r2plus1d(rgb=rgb, flow=flow, pretrained=True)
            else:
                logging.info("{} with {}.".format(model_name, attention))
                feature_network = se_r2plus1d(rgb=rgb, flow=flow, pretrained=True, attention=attention)

        elif model_name == "MC3_18":
            if not att:
                logging.info("{} without SELayer.".format(model_name))
                feature_network = mc3(rgb=rgb, flow=flow, pretrained=True)
            else:
                logging.info("{} with {}.".format(model_name, attention))
                feature_network = se_mc3(rgb=rgb, flow=flow, pretrained=True, attention=attention)
    feature_network.update({"audio": None})
    return feature_network, int(class_feature_dim), int(domain_feature_dim)


def get_extractor_feat(model_name, image_modality, dict_num_classes, frame_aggregation, segments, input_size=1024, output_size=256):
    """Get the feature extractor w/o SELayers for feature input.
    """
    rgb, flow, audio = get_image_modality(image_modality)

    if model_name == "TA3N":
        logging.info("{}".format(model_name))
        feature_network = ta3n_joint(rgb, flow, audio, input_size, output_size, input_type="feature",
                                     frame_aggregation=frame_aggregation, segments=segments,
                                     dict_n_class=dict_num_classes)

    domain_feature_dim = int(output_size)
    if rgb:
        if flow:
            if audio:  # For all inputs
                class_feature_dim = int(domain_feature_dim * 3)
            else:  # For joint(rgb+flow) input
                class_feature_dim = int(domain_feature_dim * 2)
        else:
            if audio:  # For rgb+audio input
                class_feature_dim = int(domain_feature_dim * 2)
            else:  # For rgb input
                class_feature_dim = domain_feature_dim
    else:
        if flow:
            if audio:  # For flow+audio input
                class_feature_dim = int(domain_feature_dim * 2)
            else:  # For flow input
                class_feature_dim = domain_feature_dim
        else:  # For audio input
            class_feature_dim = domain_feature_dim
    class_feature_dim = int(domain_feature_dim)
    domain_feature_dim = int(domain_feature_dim)

    return feature_network, class_feature_dim, domain_feature_dim
