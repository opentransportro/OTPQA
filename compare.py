from __future__ import print_function

import json

UNRESTRICTED_MODES = set(["WALK", "BICYCLE", "CAR"])


def parsetime(aa):
    if aa is None:
        return None

    return float(aa.split()[0])


def extractdurations(filename):
    blob = json.load(open(filename))
    dataset = dict([(response["id_tuple"], response) for response in blob["responses"]])

    durations = {}

    for id_tuple in dataset:
        response = dataset[id_tuple]

        if not "itins" in response or len(response["itins"]) == 0:
            durations[id_tuple] = -1
        else:
            durations[id_tuple] = parsetime(response["itins"][0]["duration"])
    return durations


def extractitineraries(filename):
    blob = json.load(open(filename))
    dataset = dict([(response["id_tuple"], response) for response in blob["responses"]])

    itineraries = {}

    for id_tuple in dataset:
        response = dataset[id_tuple]

        if not "itins" in response:
            itineraries[id_tuple] = 0
        else:
            itineraries[id_tuple] = len(response["itins"])
    return itineraries


def extractmodes(filename):
    blob = json.load(open(filename))
    dataset = dict([(response["id_tuple"], response) for response in blob["responses"]])

    num_modes = {}

    for id_tuple in dataset:
        response = dataset[id_tuple]

        if not "itins" in response or len(response["itins"]) == 0:
            num_modes[id_tuple] = 0
        else:
            modes_set = set()
            for itinerary in response["itins"]:
                if len(set(itinerary).difference(UNRESTRICTED_MODES)) == 0:
                    modes_set.union(itinerary["leg_modes"])
                else:
                    # Do not include WALK, BICYCLE or CAR if there are other modes
                    modes_set.union(set(itinerary["leg_modes"]).difference(UNRESTRICTED_MODES))
                modes_set.union(itinerary["leg_modes"])
            num_modes[id_tuple] = len(modes_set)
    return num_modes


def extractlegs(filename):
    blob = json.load(open(filename))
    dataset = dict([(response["id_tuple"], response) for response in blob["responses"]])

    num_legs = {}

    for id_tuple in dataset:
        response = dataset[id_tuple]

        if not "itins" in response or len(response["itins"]) == 0:
            num_legs[id_tuple] = 0
        else:
            num_legs[id_tuple] = response["itins"][0]["n_legs"]
    return num_legs

def extracttrips(filename):
    blob = json.load(open(filename))
    dataset = dict([(response["id_tuple"], response) for response in blob["responses"]])

    num_trips = {}

    for id_tuple in dataset:
        response = dataset[id_tuple]

        if not "itins" in response or len(response["itins"]) == 0:
            num_trips[id_tuple] = 0
        else:
            num_trips[id_tuple] = len(response["itins"][0]["trips"])
    return num_trips


def extractspeeds(filename):
    blob = json.load(open(filename))
    dataset = dict([(response["id_tuple"], response) for response in blob["responses"]])

    walk_speeds = {}
    bicycle_speeds = {}
    walk_count = 0
    bicycle_count = 0
    walk_speed_sum = 0
    bicycle_speed_sum = 0

    for id_tuple in dataset:
        response = dataset[id_tuple]
        walk_time = 0
        walk_distance = 0
        bicycle_time = 0
        bicycle_distance = 0
        if "itins" in response:
            for itin in response["itins"]:
                if "BICYCLE" not in itin["leg_modes"]:
                    walk_distance += itin["walk_distance"]
                    i = 0
                    while i < len(itin["leg_modes"]):
                        if itin["leg_modes"][i] == "WALK":
                            walk_time += itin["leg_times"][i]
                        i += 1
                else:
                    # walk_distance includes walk and bicycle distance
                    bicycle_distance += itin["walk_distance"]
                    i = 0
                    while i < len(itin["leg_modes"]):
                        if itin["leg_modes"][i] == "WALK":
                            # remove walk distance calculated with default walk speed from bicycle_distance
                            bicycle_distance -= itin["leg_times"][i] * 1.222
                        elif itin["leg_modes"][i] == "BICYCLE":
                            bicycle_time += itin["leg_times"][i]
                        i += 1
        if bicycle_time > 0:
            response_bicycle_speed = float(bicycle_distance) / float(bicycle_time)
            bicycle_count += 1
            bicycle_speed_sum += response_bicycle_speed
            bicycle_speeds[id_tuple] = response_bicycle_speed
        elif walk_time > 0:
            response_walk_speed = float(walk_distance) / float(walk_time)
            walk_count += 1
            walk_speed_sum += response_walk_speed
            walk_speeds[id_tuple] = response_walk_speed
    average_walk_speed = 0 if walk_speed_sum is 0 else walk_speed_sum / walk_count
    average_cycling_speed = 0 if bicycle_speed_sum is 0 else bicycle_speed_sum / bicycle_count
    return {"walk_speeds": walk_speeds, "bicycle_speeds": bicycle_speeds, "average_walk_speed": average_walk_speed,
            "average_cycling_speed": average_cycling_speed}


def extractperformance(filename):
    blob = json.load(open(filename))
    dataset = dict([(response["id_tuple"], response) for response in blob["responses"]])

    total_times = {}
    avg_times = {}
    timeouts = {}

    for id_tuple in dataset:
        response = dataset[id_tuple]

        total_times[id_tuple] = response["debug"]["totalTime"]

        if response["avg_time"] != None:
            avg_times[id_tuple] = float(response["avg_time"][:5])
        else:
            avg_times[id_tuple] = 0
        timeouts[id_tuple] = response["debug"]["timedOut"]

    return {"total_times": total_times, "avg_times": avg_times, "timeouts": timeouts}


def main(args):
    fname1 = args.pop('benchmark')
    fname2 = args.pop('profile')
    threshold = args.pop('threshold')
    limit = args.pop('limit')
    itineraries = args.pop('itineraries')
    itinerary_threshold = args.pop('itinerarythreshold')
    modes = args.pop('modes')
    mode_threshold = args.pop('modethreshold')
    legs = args.pop('legs')
    leg_threshold = args.pop('legthreshold')
    trips = args.pop('trips')
    trip_threshold = args.pop('tripthreshold')
    speeds = args.pop('speeds')
    speed_threshold = args.pop('speedthreshold')
    performance = args.pop('performance')
    total_times_threshold = args.pop('totaltimethreshold')
    avg_times_threshold = args.pop('averagetimethreshold')

    print("Detecting regressions with a time threshold of %d seconds and test threshold %d " % (threshold, limit))

    dur1 = extractdurations(fname1)
    dur2 = extractdurations(fname2)

    itin1 = {}
    itin2 = {}

    if itineraries:
        print("Detecting regressions with a itinerary number threshold of %d and test threshold %d " % (
            itinerary_threshold, limit))
        itin1 = extractitineraries(fname1)
        itin2 = extractitineraries(fname2)

    modes1 = {}
    modes2 = {}

    if modes:
        print(
            "Detecting regressions with a mode number threshold of %d and test threshold %d " % (mode_threshold, limit))
        modes1 = extractmodes(fname1)
        modes2 = extractmodes(fname2)

    legs1 = {}
    legs2 = {}

    if legs:
        print("Detecting regressions with a leg number threshold of %d and test threshold %d " % (leg_threshold, limit))
        legs1 = extractlegs(fname1)
        legs2 = extractlegs(fname2)

    trips1 = {}
    trips2 = {}

    if trips:
        print("Detecting regressions with a trip number threshold of %d and test threshold %d " % (trip_threshold, limit))
        trips1 = extracttrips(fname1)
        trips2 = extracttrips(fname2)

    speeds1 = {}
    speeds2 = {}

    if speeds:
        print("Detecting regressions with a speed difference threshold of %d and test threshold %d " % (
            speed_threshold, limit))
        speeds1 = extractspeeds(fname1)
        speeds2 = extractspeeds(fname2)

    performance1 = {}
    performance2 = {}

    if performance:
        print("Detecting regressions with a total request time difference threshold of %d, an average request time difference threshold of %d, \
                           and test threshold %d " % (total_times_threshold, avg_times_threshold, limit))
        performance1 = extractperformance(fname1)
        performance2 = extractperformance(fname2)

    fails1 = 0
    fails2 = 0
    slower1 = 0
    slower2 = 0
    count = 0

    less_itin1 = 0
    less_itin2 = 0

    less_mode1 = 0
    less_mode2 = 0

    less_legs1 = 0
    less_legs2 = 0

    less_trips1 = 0
    less_trips2 = 0

    slower_walk1 = 0
    slower_walk2 = 0
    slower_bicycle1 = 0
    slower_bicycle2 = 0

    longer_totaltime1 = 0
    longer_totaltime2 = 0
    longer_avgtime1 = 0
    longer_avgtime2 = 0
    more_timeouts1 = 0
    more_timeouts2 = 0
    totaltime_sum1 = 0
    totaltime_sum2 = 0

    for id in dur1:
        if not id in dur2:
            print("test data is not comparable")
            exit(1)
        t1 = dur1[id]
        t2 = dur2[id]
        if t1 != t2:
            diffmsg = "Test route duration %s t1=%d t2=%d diff=%d" % (id, t1, t2, t2 - t1)
            if t1 < 0 and t2 > 0:
                fails1 += 1
            elif t1 > 0 and t2 < 0:
                fails2 += 1
            elif t1 > t2 + threshold:
                slower1 += 1
            elif t2 > t1 + threshold:
                slower2 += 1
            else:
                diffmsg = ""

            if diffmsg:
                print(diffmsg)

        if itineraries:
            i1 = itin1[id]
            i2 = itin2[id]

            if i1 != i2:
                diffmsg = "Test itinerarys %s t1=%d t2=%d diff=%d" % (id, i1, i2, i2 - i1)
                if i2 >= i1 + itinerary_threshold:
                    less_itin1 += 1
                elif i1 >= i2 + itinerary_threshold:
                    less_itin2 += 1
                else:
                    diffmsg = ""

                if diffmsg:
                    print(diffmsg)

        if modes:
            m1 = modes1[id]
            m2 = modes2[id]

            if m1 != m2:
                diffmsg = "Test modes %s t1=%d t2=%d diff=%d" % (id, m1, m2, m2 - m1)
                if m2 >= m1 + mode_threshold:
                    less_mode1 += 1
                elif m1 >= m2 + mode_threshold:
                    less_mode2 += 1
                else:
                    diffmsg = ""

                if diffmsg:
                    print(diffmsg)

        if legs:
            l1 = legs1[id]
            l2 = legs2[id]

            if l1 != l2:
                diffmsg = "Test legs %s t1=%d t2=%d diff=%d" % (id, l1, l2, l2 - l1)
                if l2 >= l1 + leg_threshold:
                    less_legs1 += 1
                elif l1 >= l2 + leg_threshold:
                    less_legs2 += 1
                else:
                    diffmsg = ""

                if diffmsg:
                    print(diffmsg)

        if trips:
            t1 = trips1[id]
            t2 = trips2[id]

            if t1 != t2:
                diffmsg = "Test trips %s t1=%d t2=%d diff=%d" % (id, t1, t2, t2 - t1)
                if t2 >= t1 + trip_threshold:
                    less_trips1 += 1
                elif t1 >= t2 + trip_threshold:
                    less_trips2 += 1
                else:
                    diffmsg = ""

                if diffmsg:
                    print(diffmsg)

        if speeds:
            if (id in speeds1["walk_speeds"] and id in speeds2["walk_speeds"]) or (
                    id in speeds1["bicycle_speeds"] and id in speeds2["bicycle_speeds"]):
                speed_type = "bicycle_speeds" if id in speeds1["bicycle_speeds"] else "walk_speeds"

                s1 = speeds1[speed_type][id]
                s2 = speeds2[speed_type][id]

                if s1 != s2:
                    diffmsg = "Test %s %s t1=%f t2=%f diff=%f" % (speed_type, id, s1, s2, s2 - s1)
                    if s2 >= s1 + speed_threshold:
                        if speed_type is "walk_speeds":
                            slower_walk1 += 1
                        else:
                            slower_bicycle1 += 1
                    elif s1 >= s2 + speed_threshold:
                        if speed_type is "walk_speeds":
                            slower_walk2 += 1
                        else:
                            slower_bicycle2 += 1
                    else:
                        diffmsg = ""

                    if diffmsg:
                        print(diffmsg)

        if performance:
            total_time1 = performance1["total_times"][id]
            total_time2 = performance2["total_times"][id]
            avg_times1 = performance1["avg_times"][id]
            avg_times2 = performance2["avg_times"][id]
            timeout1 = performance1["timeouts"][id]
            timeout2 = performance2["timeouts"][id]

            totaltime_sum1 += total_time1
            totaltime_sum2 += total_time2

            if total_time1 != total_time2:
                diffmsg = "Test total time %s t1=%d t2=%d diff=%d" % (
                    id, total_time1, total_time2, total_time1 - total_time2)
                if total_time1 >= total_time2 + total_times_threshold:
                    longer_totaltime1 += 1
                elif total_time2 >= total_time1 + total_times_threshold:
                    longer_totaltime2 += 1
                else:
                    diffmsg = ""

                if diffmsg:
                    print(diffmsg)

            if avg_times1 != avg_times2:
                diffmsg = "Test average time %s t1=%f t2=%f diff=%f" % (
                    id, avg_times1, avg_times2, avg_times1 - avg_times2)
                if avg_times1 >= avg_times2 + avg_times_threshold:
                    longer_avgtime1 += 1
                elif avg_times2 >= avg_times1 + avg_times_threshold:
                    longer_avgtime2 += 1
                else:
                    diffmsg = ""

                if diffmsg:
                    print(diffmsg)

            if timeout1 != timeout2:
                diffmsg = "Test timeouts %s t1=%r t2=%r" % (id, timeout1, timeout2)
                if timeout1:
                    more_timeouts1 += 1
                else:
                    more_timeouts2 += 1
                print(diffmsg)

        count += 1

    print("Test count: %d" % count)
    print("Routings that failed only in %s: %d" % (fname1, fails1))
    print("Routings that failed only in %s: %d" % (fname2, fails2))
    print("Routes that are slower in %s: %d" % (fname1, slower1))
    print("Routes that are slower in %s: %d" % (fname2, slower2))

    print("Route duration regressions: %d" % (fails2 + slower2))
    rate = int(100 * float(count + fails1 - fails2 + slower1 - slower2) / float(count))
    print("Route duration comparison rate: %d" % rate)
    fail = False
    if rate < limit:
        print("Route duration test failed, %d < %d" % (rate, limit))
        fail = True
    if itineraries:
        print("Routes that have less itineraries in %s: %d" % (fname1, less_itin1))
        print("Routes that have less itineraries in %s: %d" % (fname2, less_itin2))
        rate = int(100 * float(count + less_itin1 - less_itin2) / float(count))
        if rate < limit:
            print("Itinerary test failed, %d < %d" % (rate, limit))
            fail = True
    if modes:
        print("Routes that have less modes in %s: %d" % (fname1, less_mode1))
        print("Routes that have less modes in %s: %d" % (fname2, less_mode2))
        rate = int(100 * float(count + less_mode1 - less_mode2) / float(count))
        if rate < limit:
            print("Mode test failed, %d < %d" % (rate, limit))
            fail = True
    if legs:
        print("Routes that have less legs in %s: %d" % (fname1, less_legs1))
        print("Routes that have less legs in %s: %d" % (fname2, less_legs2))
        rate = int(100 * float(count + less_legs1 - less_legs2) / float(count))
        if rate < limit:
            print("Legs test failed, %d < %d" % (rate, limit))
            fail = True
    if trips:
        print("Routes that have less trips in %s: %d" % (fname1, less_trips1))
        print("Routes that have less trips in %s: %d" % (fname2, less_trips2))
        rate = int(100 * float(count + less_trips1 - less_trips2) / float(count))
        if rate < limit:
            print("Trips test failed, %d < %d" % (rate, limit))
            fail = True
    if speeds:
        print("Routes that have slower walk in %s: %d" % (fname1, slower_walk1))
        print("Routes that have slower cycling in %s: %d" % (fname1, slower_bicycle1))
        print("Routes that have slower walk in %s: %d" % (fname2, slower_walk2))
        print("Routes that have slower cycling in %s: %d" % (fname2, slower_bicycle2))
        rate = int(
            100 * float(count + (slower_walk1 + slower_bicycle1) - (slower_walk2 + slower_bicycle2)) / float(count))
        if rate < limit:
            print("Speed test failed, %d < %d" % (rate, limit))
            fail = True
        print("Average walk speed in %s: %f m/s" % (fname1, speeds1["average_walk_speed"]))
        print("Average cycling speed %s: %f m/s" % (fname1, speeds1["average_cycling_speed"]))
        print("Average walk speed %s: %f m/s" % (fname2, speeds2["average_walk_speed"]))
        print("Average cycling speed %s: %f m/s" % (fname2, speeds2["average_cycling_speed"]))

    if performance:
        print("Total request time of all requests summed in %s: %d" % (fname1, totaltime_sum1))
        print("Total request time of all requests summed in %s: %d" % (fname2, totaltime_sum2))
        print("Difference in total request time of all requests summed %d" % (totaltime_sum1 - totaltime_sum2))
        print("Percentage difference in total request time of all requests summed %f" % (
                (float(totaltime_sum1 - totaltime_sum2) / totaltime_sum2) * 100))
        print("Routes that have longer total request time in %s: %d" % (fname1, longer_totaltime1))
        print("Routes that have longer total request time in %s: %d" % (fname2, longer_totaltime2))
        print("Routes that have longer average request time in %s: %d" % (fname1, longer_avgtime1))
        print("Routes that have longer average request time in %s: %d" % (fname2, longer_avgtime2))
        print("Routes that have more timeouts in %s: %d" % (fname1, more_timeouts1))
        print("Routes that have more timeouts in %s: %d" % (fname2, more_timeouts2))
        rate = int(100 * float(count + longer_totaltime1 - longer_totaltime2) / float(count))
        if rate < limit:
            print("Total request time test failed, %d < %d" % (rate, limit))
            fail = True
        rate = int(100 * float(count + longer_avgtime1 - longer_avgtime2) / float(count))
        if rate < limit:
            print("Average request time test failed, %d < %d" % (rate, limit))
            fail = True
        rate = int(100 * float(count + more_timeouts1 - more_timeouts2) / float(count))
        if rate < limit:
            print("Timeout test failed, %d < %d" % (rate, limit))
            fail = True
    if fail:
        exit(1)
    print("Test passed")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description='Compare two routing profiles to detect slower routes and failed routing requests')
    parser.add_argument('benchmark')
    parser.add_argument('profile')
    parser.add_argument('-t', '--threshold', type=int,
                        default=60)  # seconds. Route duration changes less than this are ignored
    parser.add_argument('-l', '--limit', type=int,
                        default=95)  # failure limit percentage. If share of equally good routes is below this, exit with nonzero code.
    parser.add_argument('-i', '--itineraries', action='store_true', default=False)  # compare number of itineraries
    parser.add_argument('-it', '--itinerarythreshold', type=int,
                        default=1)  # Changes in number of itineraries less than this are ignored
    parser.add_argument('-m', '--modes', action='store_true', default=False)  # compare mode variation in itineraries
    parser.add_argument('-mt', '--modethreshold', type=int,
                        default=1)  # Changes in number of modes less than this are ignored
    parser.add_argument('-legs', '--legs', action='store_true',
                        default=False)  # compare number of legs in first initinerary
    parser.add_argument('-legt', '--legthreshold', type=int,
                        default=1)  # Changes in number of legs less than this are ignored
    parser.add_argument('-trips', '--trips', action='store_true',
                        default=False)  # compare number of trips in first initinerary
    parser.add_argument('-tript', '--tripthreshold', type=int,
                        default=1)  # Changes in number of legs less than this are ignored
    parser.add_argument('-s', '--speeds', action='store_true', default=False)  # compare bicycle and walk speeds in m/s
    parser.add_argument('-st', '--speedthreshold', type=float,
                        default=0.2)  # Changes in average speed (m/s) less than this is ignored
    parser.add_argument('-p', '--performance', action='store_true',
                        default=False)  # compare performance in handling requests
    parser.add_argument('-tt', '--totaltimethreshold', type=int,
                        default=200)  # Changes in total request times (ms) less than this are ignored
    parser.add_argument('-at', '--averagetimethreshold', type=int,
                        default=40)  # Changes in total request times (ms) less than this are ignored

    args = parser.parse_args()
    main(vars(args))
