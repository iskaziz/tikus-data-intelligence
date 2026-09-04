# Source Register

This document records only source behaviour already established through read-only observation. It is not a licence to infer unavailable data.

## GSC

**Capability:** schedule + public seat-state observation.

- TIKUS! parent movie ID observed: `6363`.
- TIKUS! source child code observed: `1000005309`.
- Schedule endpoint: `getShowTimesByMovie_ParentChild_V2` with `parentid` and `oprndate`.
- The schedule payload exposes native `show id`, `date`, `time`, `hid`, `hname`, and format fields.
- Read-only seat endpoint: `getHallSeatStatus` with location ID, hall ID, show date and show time.
- Seat-state normalization: `A` available; `B` booked-state; all other returned statuses retained as separately unavailable.

The collector does **not** select a seat, create a booking transaction, reserve inventory or enter payment.

## TGV

**Capability:** official API schedule + seat-state observation.

- TIKUS! movie recid: `7b2216d1-27d8-479e-b420-8ab157847aa6`.
- Observed scheduled film code includes `HO00025533`.
- Schedule endpoint: `/api/boxoffice/v1/moviesession_get`.
- Session records expose `sessionid`, `scheduledfilmid`, `showtimemy`, `screenname`, `businessdate`, `experience` and seat-type metadata.
- Seat-state endpoint: `/api/boxoffice/v1/moviesession_getseatstatus`.
- Seat fields: `seatstotal`, `seatsused`, `usedpercentage`.

`seatsused` may include held or otherwise unavailable inventory. It is never relabelled as confirmed ticket sales.

## Paragon

**Capability:** schedule-only boundary.

Canonical cinema codes:

- Batu Pahat: `0000000002`
- KTCC: `0000000004`

Prior verified schedule observations exposed booking session IDs, but a trustworthy read-only seat count was not established. The new live collector therefore does not infer seat inventory.

## Mega Cineplex

**Capability:** schedule-only boundary.

Riverfront Mall's established public listing identifier is `793`. No seat inventory is inferred.

## Collection policy

All automated acquisition in this repository is intended to be passive and read-only. No collector may automate seat selection, create temporary holds, submit an order or touch payment flows.
