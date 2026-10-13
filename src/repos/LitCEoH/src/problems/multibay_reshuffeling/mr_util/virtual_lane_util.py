import numpy as np

from problems.multibay_reshuffeling.convert_to_virtual_lanes.network_flow_model import NetworkFlowModel


def generate_virtual_lanes(wh_initial):
    all_virtual_lanes = []

    for bay in wh_initial.bays:
        bay.state = bay.state.transpose((1, 0, 2))  # I use columns instead of rows as arrays
        nfm = NetworkFlowModel(bay)

        virtual_lanes = nfm.get_virtual_lanes()
        for virtual_lane in virtual_lanes:
            virtual_lane.stacks = np.asarray(virtual_lane.stacks).flatten()
        all_virtual_lanes.extend(virtual_lanes)
        bay.state = bay.state.transpose((1, 0, 2))

    all_virtual_lanes.sort(key=lambda lane: lane.ap_id)

    return all_virtual_lanes


def get_ap_ids(lanes, ap_distance):
    ap_ids, start_ind, lane_sizes = lanes_to_inds(lanes)
    end_ind = start_ind + lane_sizes
    return ap_ids, start_ind, end_ind, lane_sizes


