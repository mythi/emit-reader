import struct
import datetime


class Emit:
    def __init__(self, bytestream):

        self.ebytes = [x ^ 223 for x in bytestream]

        if self.ebytes[0:2] != [255, 255]:
            raise ValueError('tuntematon protokolla')
        if sum(self.ebytes[2:10]) % 256:
            raise ValueError('1. tarkistussumma virheellinen')
        if sum(self.ebytes[0:217]) % 256:
            raise ValueError('2. tarkistussumma virheellinen')

        self.id = self.ebytes[2] + self.ebytes[3] * (1 << 8) + self.ebytes[4] * (1 << 16)

        self.prod_week = self.ebytes[6]
        self.prod_year = self.ebytes[7]

        self.timesys = "".join([chr(x) for x in self.ebytes[160:192]])

        self.disp1 = "".join([chr(x) for x in self.ebytes[192:200]])
        self.disp2 = "".join([chr(x) for x in self.ebytes[200:208]])
        self.disp3 = "".join([chr(x) for x in self.ebytes[208:216]])

        # TODO check
        self.battery_low = 1 if 99 in self.ebytes[10:160:3] else 0

        cps = self.ebytes[10:161:3]
        t1 = self.ebytes[11:161:3]
        t2 = self.ebytes[12:161:3]

        splits = [a + (b << 8) for a, b in zip(t1, t2)]
        self.results = [(a, b) for a, b in zip(cps, splits) if a]
        self.codes = [cp[0] for cp in self.results]

    def check_route(self, pattern, pos=0, idx=0):
        try:
            index = self.codes.index(pattern[pos], idx)
            return self.check_route(pattern, pos+1, index+1)
        except IndexError:
            return 0
        except ValueError:
            if self.codes[idx] != pattern[pos]:
                return 1
            else:
                return 0

    def count_missing(self, route):
        count = 0

        for cp in self.codes:
            if cp not in route:
                count += 1
        return count

    def find_pairs(self, start_code, end_code, idx=0):
        try:
            start = self.codes.index(start_code, idx)
            end = self.codes.index(end_code, start)

            # check missing end_code
            if start_code in self.codes[start + 1:end]:
                start = self.codes.index(start_code, start + 1)

            start_t = datetime.timedelta(seconds=self.results[start][1])
            end_t = datetime.timedelta(seconds=self.results[end][1])

            return [(start, end, end_t - start_t)] + self.find_pairs(start_code, end_code, end+1)
        except ValueError:
            return []

    def dump_raw(self):
        print("\nEMIT BYTES:\n%s\n" % " ".join(str(x) for x in self.ebytes))

    def dump_info(self):
        print("\nEMIT INFO:")
        print("\t%s" % self.id)
        print("\t%s" % self.prod_week)
        print("\t%s" % self.prod_year)
        print("\t%s" % self.timesys)
        print("\t%s" % self.disp1)
        print("\t%s" % self.disp2)
        print("\t%s" % self.disp3)

    def dump_controls(self):
        splittime = datetime.timedelta()
        prev = (0, datetime.timedelta())

        print("\nEMIT CONTROLS:")
        for cp, split in self.results:
            splittime = datetime.timedelta(seconds=split)

            # Emit time is not monotonic (clock stopped?)
            if splittime > prev[1]:
                split_str = str(splittime-prev[1])
            else:
                split_str = str(splittime)

            print('{:>4} - {:>4}{:>10}'.format(
                prev[0], cp, split_str)
                )
            prev = (cp, splittime)
        print('{:>21}'.format('-------'))
        print('{:>21}'.format(str(splittime)))

    def write_file(self, suffix=''):
        fn = "%s%s.bin" % (self.id, suffix)

        with open(fn, 'wb') as emit_file:
            emit_file.write(
                    struct.pack('<217B', *[x ^ 223 for x in self.ebytes])
                    )

        print("Kirjoitettu %s" % fn)
