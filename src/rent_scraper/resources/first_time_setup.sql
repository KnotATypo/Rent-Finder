-- =====================================================
-- Create view to simplify interation with the Address and AddressHistory tables, enforcing the creation of new rows in
-- AddressHistory when fields are updated
-- =====================================================

CREATE OR REPLACE VIEW public.simpleaddressview(id, address, beds, baths, cars) AS
SELECT a.id,
       a.address,
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
-- Same as above but with listings instead
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

-- =====================================================
-- Function to simulate a cascade delete when we remove an address to also remove related listing and address and
-- listing history
-- =====================================================

CREATE OR REPLACE FUNCTION delete_listing_and_address_data()
    RETURNS TRIGGER AS
$$
BEGIN
    -- Delete related listinghistory
    DELETE
    FROM listinghistory
    WHERE listing_id IN (SELECT l.id
                         FROM listing l
                         WHERE l.address_id = OLD.id);
    -- Delete related listings
    DELETE FROM listing WHERE address_id = OLD.id;
    -- Delete related addresshistory
    DELETE FROM addresshistory WHERE address_id = OLD.id;
    RETURN OLD;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_delete_address
    BEFORE DELETE
    ON address
    FOR EACH ROW
EXECUTE FUNCTION delete_listing_and_address_data();