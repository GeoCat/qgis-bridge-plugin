<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:xs="http://www.w3.org/2001/XMLSchema"
                xmlns:gml="http://www.opengis.net/gml" xmlns:gmd="http://www.isotc211.org/2005/gmd"
                xmlns:gco="http://www.isotc211.org/2005/gco"
                xmlns="http://qgis.org/resource-metadata/1.0"
                exclude-result-prefixes="xs"
                version="1.0">
    
    
    <xsl:template match="gmd:MD_Metadata">
        <qgis>

            <identifier><xsl:value-of select="gmd:fileIdentifier/gco:CharacterString"/></identifier>
            <parentidentifier><xsl:value-of select="gmd:parentIdentifier/gco:CharacterString"/></parentidentifier>
            <language><xsl:value-of select="gmd:language/gmd:LanguageCode/@codeListValue"/></language>
            <type><xsl:value-of select="gmd:hierarchyLevel/gmd:MD_ScopeCode/@codeListValue"/></type>
            
            <title><xsl:value-of select="gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:title/gco:CharacterString"/></title>
            <abstract><xsl:value-of select="gmd:identificationInfo/gmd:MD_DataIdentification/gmd:abstract/gco:CharacterString"/></abstract>
            
            <xsl:if test="count(gmd:identificationInfo/gmd:MD_DataIdentification/gmd:descriptiveKeywords[not(gmd:MD_Keywords/gmd:thesaurusName)]) > 0">
                <keywords vocabulary="">
                    <xsl:for-each select="gmd:identificationInfo/gmd:MD_DataIdentification/gmd:descriptiveKeywords/gmd:MD_Keywords/gmd:keyword">
                        <keyword>
                            <xsl:value-of select="gco:CharacterString" />
                        </keyword>
                    </xsl:for-each>            
                </keywords>
            </xsl:if>
            
            <xsl:if test="count(gmd:identificationInfo/gmd:MD_DataIdentification/gmd:descriptiveKeywords[gmd:MD_Keywords/gmd:thesaurusName]) > 0">
                <xsl:for-each select="gmd:identificationInfo/gmd:MD_DataIdentification/gmd:descriptiveKeywords[gmd:MD_Keywords/gmd:thesaurusName]">
                    <keywords vocabulary="{gmd:MD_Keywords/gmd:thesaurusName/gmd:CI_Citation/gmd:title/gco:CharacterString}">                    
                        <xsl:for-each select="gmd:MD_Keywords/gmd:keyword">
                            <keyword>
                                <xsl:value-of select="gco:CharacterString" />
                            </keyword>
                        </xsl:for-each>
                    </keywords>
                </xsl:for-each>            
            </xsl:if>
            
            <!-- Topic categories -->   
            <xsl:if test="count(gmd:identificationInfo/gmd:MD_DataIdentification/gmd:topicCategory) > 0">
                <keywords vocabulary="gmd:topicCategory">
                    <xsl:for-each select="gmd:identificationInfo/gmd:MD_DataIdentification/gmd:topicCategory">
                        <keyword><xsl:value-of select="gmd:MD_TopicCategoryCode" /></keyword>
                    </xsl:for-each>
                </keywords>
            </xsl:if>       
            
            <!-- Metadata dataset contact -->
            <xsl:call-template name="contact">
                <xsl:with-param name="element" select="gmd:identificationInfo/gmd:MD_DataIdentification/gmd:pointOfContact" />
            </xsl:call-template>
            
            <links>
                <xsl:for-each select="gmd:distributionInfo/gmd:MD_Distribution/gmd:transferOptions/gmd:MD_DigitalTransferOptions/gmd:onLine/gmd:CI_OnlineResource">
                    <xsl:variable name="protocol">
                        <xsl:choose>
                            <!-- GeoNetwork special value -->
                            <xsl:when test="gmd:protocol/gco:CharacterString='WWW:LINK-1.0-http--link'">WWW:LINK</xsl:when>
                            <xsl:otherwise><xsl:value-of select="gmd:protocol/gco:CharacterString" /></xsl:otherwise>
                        </xsl:choose>
                    </xsl:variable>
                    
                    <link url="{gmd:linkage/gmd:URL}" type="{$protocol}" name="{gmd:name/gco:CharacterString}" description="{gmd:description/gco:CharacterString}" />
                </xsl:for-each>
            </links>
            
            <!-- Metadata contact -->
            <xsl:call-template name="contact">
                <xsl:with-param name="element" select="gmd:contact" />
            </xsl:call-template>
            
            <!-- Distributor contact -->
            <xsl:for-each select="gmd:distributionInfo/gmd:MD_Distribution/gmd:distributor/gmd:MD_Distributor">
                <xsl:call-template name="contact">
                    <xsl:with-param name="element" select="gmd:distributorContact" />
                </xsl:call-template>
            </xsl:for-each>
            
            <!-- Dataset contact -->
            <xsl:call-template name="contact">
                <xsl:with-param name="element" select="gmd:identificationInfo/gmd:MD_DataIdentification/gmd:contact" />
            </xsl:call-template>
            
            
            <!-- Fees -->
            <xsl:for-each select="gmd:identificationInfo/gmd:MD_DataIdentification/gmd:resourceConstraints/gmd:MD_Constraints/gmd:useLimitation">
                <fees><xsl:value-of select="gco:CharacterString"/></fees>
            </xsl:for-each>
        
            <!-- Use constraints -->
            <xsl:for-each select="gmd:identificationInfo/gmd:MD_DataIdentification/gmd:resourceConstraints/gmd:MD_LegalConstraints/gmd:useConstraints">
                <constraints type="use"><xsl:value-of select="gmd:MD_RestrictionCode/@codeListValue"/></constraints>
            </xsl:for-each>
            
            <!-- Access constraints -->
            <xsl:for-each select="gmd:identificationInfo/gmd:MD_DataIdentification/gmd:resourceConstraints/gmd:MD_LegalConstraints/gmd:accessConstraints">
                <constraints type="access"><xsl:value-of select="gmd:MD_RestrictionCode/@codeListValue"/></constraints>
            </xsl:for-each>
            
            <!-- Other constraints -->
            <xsl:for-each select="gmd:identificationInfo/gmd:MD_DataIdentification/gmd:resourceConstraints/gmd:MD_LegalConstraints/gmd:otherConstraints">
                <constraints type="other"><xsl:value-of select="gco:CharacterString"/></constraints>
            </xsl:for-each>
            
            <!-- License and constraints -->
            <xsl:for-each select="gmd:identificationInfo/gmd:MD_DataIdentification/gmd:resourceConstraints/gmd:MD_LegalConstraints/gmd:otherConstraints">
                <license><xsl:value-of select="gco:CharacterString"/></license>
            </xsl:for-each>
            
            <xsl:if test="gmd:referenceSystemInfo/gmd:MD_ReferenceSystem/gmd:referenceSystemIdentifier/gmd:RS_Identifier/gmd:code">
                <crs>
                    <spatialrefsys>
                        <authid><xsl:value-of select="gmd:referenceSystemInfo/gmd:MD_ReferenceSystem/gmd:referenceSystemIdentifier/gmd:RS_Identifier/gmd:code/gco:CharacterString"/></authid>
                    </spatialrefsys>
                </crs>
            </xsl:if>
            
            
            <!-- Temporal extent -->
            <extent>
                <xsl:if test="string(gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:temporalElement/gmd:EX_TemporalExtent/gmd:extent/gml:TimePeriod/gml:beginPosition) or
                    string(gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:temporalElement/gmd:EX_TemporalExtent/gmd:extent/gml:TimePeriod/gml:endPosition)">
                    
                    <temporal>
                        <period>
                            <start><xsl:value-of select="gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:temporalElement/gmd:EX_TemporalExtent/gmd:extent/gml:TimePeriod/gml:beginPosition"/></start>
                            <end><xsl:value-of select="gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent/gmd:EX_Extent/gmd:temporalElement/gmd:EX_TemporalExtent/gmd:extent/gml:TimePeriod/gml:endPosition"/></end>
                        </period>
                    </temporal>
                    
                </xsl:if>
                <spatial crs="EPSG:4326" minx="{gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent[gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox][1]/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox/gmd:westBoundLongitude/gco:Decimal}" 
                    maxx="{gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent[gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox][1]/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox/gmd:eastBoundLongitude/gco:Decimal}" 
                    miny="{gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent[gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox][1]/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox/gmd:southBoundLatitude/gco:Decimal}" 
                    maxy="{gmd:identificationInfo/gmd:MD_DataIdentification/gmd:extent[gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox][1]/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox/gmd:northBoundLatitude/gco:Decimal}" />
            </extent>
            
            
      
        </qgis>
    </xsl:template>
   
       
    <xsl:template name="contact">
        <xsl:param name="element" />
        
        <contact>
            <name><xsl:value-of select="$element/gmd:CI_ResponsibleParty/gmd:individualName/gco:CharacterString"/></name>
            <organization><xsl:value-of select="$element/gmd:CI_ResponsibleParty/gmd:organisationName/gco:CharacterString"/></organization>
            <position><xsl:value-of select="$element/gmd:CI_ResponsibleParty/gmd:positionName/gco:CharacterString"/></position>
            <voice><xsl:value-of select="$element/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:phone/gmd:CI_Telephone/gmd:voice/gco:CharacterString"/></voice>
            <fax><xsl:value-of select="$element/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:phone/gmd:CI_Telephone/gmd:fax/gco:CharacterString"/></fax>
            <role><xsl:value-of select="$element/gmd:CI_ResponsibleParty/gmd:role/gmd:CI_RoleCode/@codeListValue"/></role>
            
            <xsl:for-each select="gmd:address/gmd:CI_Address">
                <email><xsl:value-of select="gmd:electronicMailAddress/gco:CharacterString"/></email>
                
                <contactAddress type='postal'>
                    <address><xsl:value-of select="gmd:deliveryPoint/gco:CharacterString"/></address>
                    <city><xsl:value-of select="gmd:city/gco:CharacterString"/></city>
                    <administrativearea><xsl:value-of select="gmd:administrativeArea/gco:CharacterString"/></administrativearea>
                    <postalcode><xsl:value-of select="gmd:postalCode/gco:CharacterString"/></postalcode>
                    <country><xsl:value-of select="gmd:country/gco:CharacterString"/></country>
                </contactAddress>
            </xsl:for-each>
        </contact>
    </xsl:template>

</xsl:stylesheet>