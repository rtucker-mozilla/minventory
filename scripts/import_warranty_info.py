__import__('inventory_context')
from systems.models import System
import datetime
import csv


def wimport(reader, lookups, date_format):
    total_records = 0
    updated = 0
    missing = 0
    for row in reader:
        total_records += 1
        warranty_start, warranty_end, serial = (
            row[lookups['warranty_start']], row[lookups['warranty_end']],
            row[lookups['serial']]
        )
        serial = serial.strip("'")  # Not sure why there is a ' mark

        try:
            s = System.objects.get(serial=serial)
        except System.DoesNotExist:
            print "No system in Inventory with serial '%s'" % serial
            missing += 1
            continue
        except System.MultipleObjectsReturned:
            print "Multiple system in Inventory with serial '%s'" % serial
            for s in System.objects.filter(serial=serial):
                print (
                    "\thttps://inventory.mozilla.org/systems/show/%s/ %s" %
                    (s.pk, s.hostname)
                )

        if not s.warranty_end:
            updated += 1
        s.warranty_start = datetime.datetime.strptime(
            warranty_start, date_format)
        s.warranty_end = datetime.datetime.strptime(warranty_end, date_format)
        s.save()

    print "Total number of records in spreadsheet: %s" % total_records
    print "Total number of records that were not in Inventory: %s" % missing  # noqa
    print "Matched %s records" % (total_records - missing)  # noqa
    print "\nUpdated %s records who previously didn't have warranty info" % (updated)  # noqa

if __name__ == '__main__':

    def i(fname, lookups, date_format='%d-%b-%y'):
        print "%s Importing %s" % ('=' * 90, fname)
        with open(fname, 'r') as csvfile:
            wimport(csv.DictReader(csvfile), lookups, date_format)

    i('juniper_warranty.csv', {
        'warranty_start': 'Ship Date',
        'warranty_end': 'Warranty End Date',
        'serial': 'Serial #'
    })
