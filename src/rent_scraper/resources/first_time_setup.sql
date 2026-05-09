CREATE OR REPLACE VIEW public.simpleaddressview(id, beds, baths, cars) AS
SELECT a.id,
       ah.beds,
       ah.baths,
       ah.cars
FROM address a
         JOIN (SELECT address_id,
                      beds,
                      baths,
                      cars,
                      valid_from,
                      ROW_NUMBER()
                      OVER (PARTITION BY address_id ORDER BY valid_from DESC) AS rn
               FROM addresshistory) ah ON ah.address_id = a.id
WHERE ah.rn = 1;

CREATE OR REPLACE FUNCTION update_address_history()
    RETURNS TRIGGER AS
$$
BEGIN
    IF OLD.beds != NEW.beds OR OLD.baths != NEW.baths OR OLD.cars != NEW.cars THEN
        INSERT INTO addresshistory (address_id, beds, baths, cars, valid_from)
        VALUES (OLD.id, NEW.beds, NEW.baths, NEW.cars, NOW());
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER update_address
    INSTEAD OF UPDATE
    ON simpleaddressview
    FOR EACH ROW
EXECUTE FUNCTION update_address_history();

-- =====================================================

CREATE OR REPLACE VIEW public.simplelistingview(id, address_id, price, available) AS
SELECT l.id,
       l.address_id,
       lh.price,
       lh.valid_until IS NULL AS available
FROM listing l
         JOIN (SELECT listing_id,
                      price,
                      valid_from,
                      valid_until,
                      ROW_NUMBER()
                      OVER (PARTITION BY listing_id ORDER BY valid_from DESC) AS rn
               FROM listinghistory) lh ON lh.listing_id = l.id
WHERE lh.rn = 1;

CREATE OR REPLACE FUNCTION update_listing_history()
    RETURNS TRIGGER AS
$$
BEGIN
    IF NEW.available AND OLD.available AND OLD.price != NEW.price THEN
--      Price update
        UPDATE listinghistory SET valid_until = NOW() WHERE listing_id = OLD.id AND valid_until IS NULL;
        INSERT INTO listinghistory (listing_id, price, valid_from) VALUES (OLD.id, NEW.price, NOW());
    ELSEIF NOT NEW.available THEN
--      Availability update
        UPDATE listinghistory SET valid_until = NOW() WHERE listing_id = OLD.id AND valid_until IS NULL;
    ELSEIF NOT OLD.available AND NEW.available THEN
--      Listing being made available again
        INSERT INTO listinghistory (listing_id, price, valid_from) VALUES (OLD.id, NEW.price, NOW());
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER update_listing
    INSTEAD OF UPDATE
    ON simplelistingview
    FOR EACH ROW
EXECUTE FUNCTION update_listing_history();