#!/usr/bin/env python

# Untracked manual control operation using joystick, doesnt work yet










# vim:set ts=4 sw=4 et:
#
# Copyright 2014 Vladimir Ermakov.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License
# for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA

from __future__ import print_function

import sys
import argparse

import rospy
from sensor_msgs.msg import Joy
from mavros_msgs.msg import OverrideRCIn


def arduino_map(x, inmin, inmax, outmin, outmax):
    return (x - inmin) * (outmax - outmin) / (inmax - inmin) + outmin


class RCChan(object):
    def __init__(self, name, chan, min_pos=-1.0):
        self.name = name
        self.chan = chan
        self.min = 1000
        self.max = 2000
        self.min_pos = min_pos

    def load_param(self):
        self.chan = rospy.get_param("~rc_map/" + self.name, self.chan)
        self.min = rospy.get_param("~rc_min/" + self.name, self.min)
        self.max = rospy.get_param("~rc_max/" + self.name, self.max)

    def calc_us(self, pos):
        # warn: limit check
        return arduino_map(pos, self.min_pos, 1.0, self.min, self.max)


# Mode 2 on Logitech F710 gamepad
axes_map = {
    'roll': 3,
    'pitch': 4,
    'yaw': 0,
    'throttle': 1
}

axes_scale = {
    'roll': 1.0,
    'pitch': 1.0,
    'yaw': 1.0,
    'throttle': 1.0
}

# XXX: todo
button_map = {
    'takeoff': 0,
    'land': 1,
    'enable': 2
}


rc_channels = {
    'roll': RCChan('roll', 0),
    'pitch': RCChan('pitch', 1),
    'yaw': RCChan('yaw', 3),
    'throttle': RCChan('throttle', 2, 0.0)
}



def rc_override_control(args):
    rospy.init_node("mavteleop")
    rospy.loginfo("MAV-Teleop: RC Override control type.")

    def load_map(m, n):
        for k, v in m.iteritems():
            m[k] = rospy.get_param(n + k, v)

    load_map(axes_map, '~axes_map/')
    load_map(axes_scale, '~axes_scale/')
    load_map(button_map, '~button_map/')
    for k, v in rc_channels.iteritems():
        v.load_param()

    override_pub = rospy.Publisher(args.mavros_ns + "rc/override", OverrideRCIn, queue_size=10)

    def joy_cb(joy):
        def get_axes(n):
            return joy.axes[axes_map[n]] * axes_scale[n]

        # get axes normalized to -1.0..+1.0 RPY, 0.0..1.0 T
        roll = get_axes('roll')
        pitch = get_axes('pitch')
        yaw = get_axes('yaw')
        throttle = arduino_map(get_axes('throttle'), -1.0, 1.0, 0.0, 1.0)

        rospy.logdebug("RPYT: %f, %f, %f, %f", roll, pitch, yaw, throttle)

        rc = OverrideRCIn()
        def set_chan(n, v):
            ch = rc_channels[n]
            rc.channels[ch.chan] = ch.calc_us(v)
            rospy.logdebug("RC%d (%s): %d us", ch.chan, ch.name, ch.calc_us(v))

        # XXX: buttons
        set_chan('roll', roll)
        set_chan('pitch', pitch)
        set_chan('yaw', yaw)
        set_chan('throttle', throttle)
        override_pub.publish(rc)


    jsub = rospy.Subscriber("/joy", Joy, joy_cb)
    rospy.spin()


def main():
    parser = argparse.ArgumentParser(description="Teleoperation script for Copter-UAV")
    parser.add_argument('-n', '--mavros-ns', help="ROS node namespace", default="/mavros")
    parser.add_argument('-v', '--verbose', action='store_true', help="verbose output")
    parser.add_argument('-rc', '--rc-override', action='store_true', help="use rc override control type")

    args = parser.parse_args(rospy.myargv(argv=sys.argv)[1:])

    if args.rc_override:
        rc_override_control(args)
    else:
        raise NotImplementedError


if __name__ == '__main__':
    main()
