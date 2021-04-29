<?xml version="1.0" encoding="UTF-8"?>
<!-- - - - - - - - - - - - - - - - - - - - - - - - - - - - - 

Transformation to produce ISO19139 documents from input documents that
combine "extra" elements (Esri-specific or from ISO19115 DTD) with an included
MD_Metadata element.

The current version ignores all elements except for MD_Metadata, which is copied to the output verbatim.

author Heikki Doeleman
- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -->
<xsl:stylesheet version="2.0" 
xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:gmd="http://www.isotc211.org/2005/gmd"
xmlns:gco="http://www.isotc211.org/2005/gco"
                xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
exclude-result-prefixes="#all"
>
	<xsl:output method="xml" version="1.0" encoding="UTF-8" indent="yes"/>
  
	<!-- the input document is supposed to have either <metadata> or <Metadata> as root element -->
	<xsl:template match="/metadata|/Metadata" priority ="10">
		<xsl:apply-templates/>
	</xsl:template>

	<!-- the wrapped <MD_Metadata> is copied in its entirety to the output -->
	<xsl:template match="gmd:MD_Metadata" priority ="10">
    <gmd:MD_Metadata
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            xmlns:gmd="http://www.isotc211.org/2005/gmd"
            xmlns:gco="http://www.isotc211.org/2005/gco"
            xsi:schemaLocation="http://www.isotc211.org/2005/gmd http://schemas.opengis.net/iso/19139/20060504/gmd/gmd.xsd">
  
      <xsl:apply-templates/>
    </gmd:MD_Metadata>
  </xsl:template>
		
  <xsl:template match="gmd:metadataStandardName" priority ="10">
    <gmd:metadataStandardName>
      <gco:CharacterString>ISO 19115</gco:CharacterString>
    </gmd:metadataStandardName>
  </xsl:template>

  <xsl:template match="gmd:metadataStandardVersion" priority ="10">
    <gmd:metadataStandardVersion>
      <gco:CharacterString>Nederlands metadata profiel op ISO 19115 voor geografie 2.0</gco:CharacterString>
    </gmd:metadataStandardVersion>
  </xsl:template>
  
  <!-- all these "extra" elements below are ignored -->
		
	<!-- ignore -->
	<xsl:template match="MetaID|Esri|FC_FeatureCatalogue|idinfo|dataIdInfo|metainfo|mdLang|mdStanName|mdStanVer|mdChar|mdHrLv|mdHrLvName|distinfo|distInfo|spdoinfo|spatRepInfo|eainfo|mdDateSt|spref|refSysInfo|dqInfo|Binary|dataqual|mdFileID|mdContact|dataset_description|ESRI_NL" priority ="10">
	</xsl:template>
  
  <!-- ignore -->
  <xsl:template match="gmd:MD_Metadata[name(parent::node())='gmd:MD_Metadata']" priority="10" />
  
  <!-- ignore -->
<!--
  <xsl:template match="gmd:*">
    <xsl:element name="gmd:{local-name()}" namespace="{namespace-uri()}">
      <xsl:copy-of select="@*"/>
      <xsl:apply-templates select="node()" />
    </xsl:element>
  </xsl:template>
-->

  <xsl:template match="@*|node()">
        <xsl:copy>
            <xsl:apply-templates select="@*|node()"/>
        </xsl:copy>
    </xsl:template>
</xsl:stylesheet>
